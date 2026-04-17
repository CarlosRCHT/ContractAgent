import os
import copy
import logging
from datetime import datetime, timezone
from typing import Optional

from lxml import etree
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT

logger = logging.getLogger(__name__)

# OpenXML namespaces
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": WORD_NS}


def qn(tag: str) -> str:
    """Create a qualified name in the Word namespace.

    Example::

        qn('w:del') -> '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}del'
    """
    prefix, local = tag.split(":")
    return f"{{{NSMAP[prefix]}}}{local}"


class RedlineResult:
    """Result of applying a single redline change."""

    def __init__(self, original_text: str, replacement_text: str):
        self.original_text = original_text
        self.replacement_text = replacement_text
        self.applied = False
        self.comment_added = False
        self.error = ""


class RedlineEngine:
    """Applies tracked changes and comments to Word documents using OpenXML manipulation."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.doc = Document(file_path)
        self._comment_id_counter = 0
        self._revision_id_counter = 100  # Start high to avoid conflicts with existing IDs
        self._comments_part = None
        self._comments_element = None
        self._ensure_comments_part()

    # ------------------------------------------------------------------
    # Internal ID generators
    # ------------------------------------------------------------------

    def _next_comment_id(self) -> int:
        self._comment_id_counter += 1
        return self._comment_id_counter

    def _next_revision_id(self) -> int:
        self._revision_id_counter += 1
        return self._revision_id_counter

    # ------------------------------------------------------------------
    # Comments part management
    # ------------------------------------------------------------------

    def _ensure_comments_part(self):
        """Ensure the document has a ``comments.xml`` part.  Create it if missing."""
        doc_part = self.doc.part

        # Check if a comments part already exists
        for rel in doc_part.rels.values():
            if "comments" in rel.reltype:
                self._comments_part = rel.target_part
                self._comments_element = etree.fromstring(self._comments_part.blob)
                # Find the highest existing comment ID so new IDs don't collide
                for comment in self._comments_element.findall(qn("w:comment")):
                    cid = int(comment.get(qn("w:id"), "0"))
                    if cid >= self._comment_id_counter:
                        self._comment_id_counter = cid + 1
                return

        # No comments part found — create one from scratch
        comments_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:comments'
            ' xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
            ' xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"'
            "/>"
        )
        self._comments_element = etree.fromstring(comments_xml.encode("utf-8"))

        from docx.opc.part import Part
        from docx.opc.packuri import PackURI

        comments_part = Part(
            PackURI("/word/comments.xml"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
            etree.tostring(
                self._comments_element,
                xml_declaration=True,
                encoding="UTF-8",
                standalone=True,
            ),
            doc_part.package,
        )
        doc_part.relate_to(
            comments_part,
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments",
        )
        self._comments_part = comments_part

    def _add_comment_to_part(
        self, comment_id: int, author: str, text: str, date_str: str
    ):
        """Add a ``<w:comment>`` element to the ``comments.xml`` part."""
        comment_el = etree.SubElement(self._comments_element, qn("w:comment"))
        comment_el.set(qn("w:id"), str(comment_id))
        comment_el.set(qn("w:author"), author)
        comment_el.set(qn("w:date"), date_str)
        comment_el.set(qn("w:initials"), author[:2].upper())

        # Paragraph inside the comment
        p = etree.SubElement(comment_el, qn("w:p"))

        # Paragraph properties — CommentText style
        pPr = etree.SubElement(p, qn("w:pPr"))
        pStyle = etree.SubElement(pPr, qn("w:pStyle"))
        pStyle.set(qn("w:val"), "CommentText")

        # Run with annotationRef (required by Word to link the comment)
        r = etree.SubElement(p, qn("w:r"))
        rPr = etree.SubElement(r, qn("w:rPr"))
        rStyle = etree.SubElement(rPr, qn("w:rStyle"))
        rStyle.set(qn("w:val"), "CommentReference")
        etree.SubElement(r, qn("w:annotationRef"))

        # Run with the actual comment text
        r2 = etree.SubElement(p, qn("w:r"))
        t = etree.SubElement(r2, qn("w:t"))
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = text

    # ------------------------------------------------------------------
    # Text search across runs
    # ------------------------------------------------------------------

    def _find_text_in_paragraphs(self, search_text: str) -> list[tuple]:
        """Locate *search_text* within document paragraphs.

        Word frequently splits a single logical string across multiple
        ``<w:r>`` (run) elements for formatting reasons, so we must
        reconstruct the full paragraph text, perform the search, and then
        map the character offsets back to the individual runs.

        Returns a list of tuples, one per occurrence::

            (paragraph, [(run_index, overlap_start, overlap_end), ...],
             match_start_in_paragraph, match_end_in_paragraph)

        * *paragraph* — the ``docx.text.paragraph.Paragraph`` object.
        * *affected_runs* — which runs contain portions of the matched
          text, with character offsets *relative to each run's own text*.
        * *match_start* / *match_end* — character offsets within the
          concatenated paragraph text (useful for ordering/deduplication).
        """
        results: list[tuple] = []
        search_lower = search_text.lower()

        for paragraph in self.doc.paragraphs:
            # Build the concatenated paragraph text and a run-map
            full_text = ""
            run_map: list[tuple[int, int, int]] = []  # (run_idx, char_start, char_end)

            for i, run in enumerate(paragraph.runs):
                start = len(full_text)
                full_text += run.text or ""
                run_map.append((i, start, len(full_text)))

            # Slide through the full text looking for every occurrence
            pos = 0
            while True:
                idx = full_text.lower().find(search_lower, pos)
                if idx == -1:
                    break

                match_start = idx
                match_end = idx + len(search_text)

                # Determine which runs overlap with [match_start, match_end)
                affected_runs: list[tuple[int, int, int]] = []
                for run_idx, run_start, run_end in run_map:
                    if run_start < match_end and run_end > match_start:
                        overlap_start = max(match_start, run_start) - run_start
                        overlap_end = min(match_end, run_end) - run_start
                        affected_runs.append((run_idx, overlap_start, overlap_end))

                if affected_runs:
                    results.append((paragraph, affected_runs, match_start, match_end))

                pos = idx + 1

        return results

    # ------------------------------------------------------------------
    # Core tracked-change application
    # ------------------------------------------------------------------

    def apply_tracked_change(
        self,
        original_text: str,
        replacement_text: str,
        author: str,
        rationale: str,
        risk_level: str = "moderate",
        date_str: str = "",
    ) -> RedlineResult:
        """Apply a single tracked change with an accompanying comment.

        1. Locate *original_text* in the document (case-insensitive).
        2. Wrap it in ``<w:del>`` (using ``<w:delText>`` for the content).
        3. Insert *replacement_text* inside ``<w:ins>`` immediately after.
        4. Bracket the region with ``commentRangeStart`` / ``commentRangeEnd``
           and add a ``commentReference`` so *rationale* appears as a Word
           comment anchored to the changed text.
        """
        result = RedlineResult(original_text, replacement_text)

        if not date_str:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        matches = self._find_text_in_paragraphs(original_text)

        if not matches:
            result.error = f"Text not found in document: '{original_text[:50]}...'"
            logger.warning(result.error)
            return result

        # Apply only to the first match
        paragraph, affected_runs, _match_start, _match_end = matches[0]
        p_element = paragraph._element

        comment_id = self._next_comment_id()
        rev_del_id = self._next_revision_id()
        rev_ins_id = self._next_revision_id()

        risk_emoji = {"major": "🔴", "moderate": "🟡", "minor": "🟢"}.get(
            risk_level, "🟡"
        )
        comment_text = f"{risk_emoji} [{risk_level.upper()}] {rationale}"

        # ---- Add the comment to comments.xml ----
        self._add_comment_to_part(comment_id, author, comment_text, date_str)

        # ---- Manipulate paragraph XML ----
        runs = paragraph.runs
        first_run_idx = affected_runs[0][0]
        first_run_element = runs[first_run_idx]._element

        # 1. commentRangeStart — placed immediately before the first affected run
        comment_range_start = etree.Element(qn("w:commentRangeStart"))
        comment_range_start.set(qn("w:id"), str(comment_id))
        first_run_element.addprevious(comment_range_start)

        # 2. Build <w:del> containing a <w:r>/<w:delText> for each affected run
        del_element = etree.Element(qn("w:del"))
        del_element.set(qn("w:id"), str(rev_del_id))
        del_element.set(qn("w:author"), author)
        del_element.set(qn("w:date"), date_str)

        for run_idx, overlap_start, overlap_end in affected_runs:
            run = runs[run_idx]
            run_el = run._element
            run_text = run.text or ""

            # If the match starts mid-run, split off the preceding text
            if overlap_start > 0:
                before_text = run_text[:overlap_start]
                before_run = copy.deepcopy(run_el)
                for t in before_run.findall(qn("w:t")):
                    t.text = before_text
                    t.set(
                        "{http://www.w3.org/XML/1998/namespace}space", "preserve"
                    )
                run_el.addprevious(before_run)

            # If the match ends mid-run, split off the trailing text
            if overlap_end < len(run_text):
                after_text = run_text[overlap_end:]
                after_run = copy.deepcopy(run_el)
                for t in after_run.findall(qn("w:t")):
                    t.text = after_text
                    t.set(
                        "{http://www.w3.org/XML/1998/namespace}space", "preserve"
                    )
                run_el.addnext(after_run)

            # Create a deletion run: copy formatting, replace <w:t> with <w:delText>
            del_run = copy.deepcopy(run_el)
            for t in del_run.findall(qn("w:t")):
                del_run.remove(t)
            del_text_el = etree.SubElement(del_run, qn("w:delText"))
            del_text_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            del_text_el.text = run_text[overlap_start:overlap_end]

            del_element.append(del_run)

            # Remove the original run from the paragraph
            p_element.remove(run_el)

        # Place <w:del> right after commentRangeStart
        comment_range_start.addnext(del_element)

        # 3. Build <w:ins> if there is replacement text
        if replacement_text:
            ins_element = etree.Element(qn("w:ins"))
            ins_element.set(qn("w:id"), str(rev_ins_id))
            ins_element.set(qn("w:author"), author)
            ins_element.set(qn("w:date"), date_str)

            ins_run = etree.SubElement(ins_element, qn("w:r"))

            # Preserve formatting from the first affected run
            original_rPr = runs[affected_runs[0][0]]._element.find(qn("w:rPr"))
            if original_rPr is not None:
                ins_run.insert(0, copy.deepcopy(original_rPr))

            ins_text = etree.SubElement(ins_run, qn("w:t"))
            ins_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            ins_text.text = replacement_text

            del_element.addnext(ins_element)
            anchor = ins_element
        else:
            anchor = del_element

        # 4. commentRangeEnd + commentReference run
        comment_range_end = etree.Element(qn("w:commentRangeEnd"))
        comment_range_end.set(qn("w:id"), str(comment_id))
        anchor.addnext(comment_range_end)

        comment_ref_run = etree.Element(qn("w:r"))
        comment_ref_rPr = etree.SubElement(comment_ref_run, qn("w:rPr"))
        comment_ref_style = etree.SubElement(comment_ref_rPr, qn("w:rStyle"))
        comment_ref_style.set(qn("w:val"), "CommentReference")
        comment_ref = etree.SubElement(comment_ref_run, qn("w:commentReference"))
        comment_ref.set(qn("w:id"), str(comment_id))
        comment_range_end.addnext(comment_ref_run)

        result.applied = True
        result.comment_added = True
        logger.info(
            "Applied tracked change: '%s...' -> '%s...'",
            original_text[:30],
            replacement_text[:30],
        )

        return result

    # ------------------------------------------------------------------
    # Batch application
    # ------------------------------------------------------------------

    def apply_all_changes(
        self,
        recommendations: list[dict],
        author: str = "Contract Review Agent",
    ) -> list[RedlineResult]:
        """Apply a list of recommended changes to the document.

        Each item in *recommendations* must be a dict with at least::

            {
                "original_text": str,
                "replacement_text": str,   # optional — defaults to ""
                "rationale": str,
                "risk_level": str,         # optional — "major"/"moderate"/"minor"
            }
        """
        results: list[RedlineResult] = []
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        for rec in recommendations:
            result = self.apply_tracked_change(
                original_text=rec["original_text"],
                replacement_text=rec.get("replacement_text", ""),
                author=author,
                rationale=rec["rationale"],
                risk_level=rec.get("risk_level", "moderate"),
                date_str=date_str,
            )
            results.append(result)

        return results

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, output_path: str = "") -> str:
        """Persist the modified document to disk.

        Updates the ``comments.xml`` part blob before saving so that all
        comments added during this session are included in the output file.
        Returns the resolved output path.
        """
        if not output_path:
            name, ext = os.path.splitext(self.file_path)
            output_path = f"{name}_redlined{ext}"

        # Flush in-memory comment elements back into the part blob
        if self._comments_part is not None:
            self._comments_part._blob = etree.tostring(
                self._comments_element,
                xml_declaration=True,
                encoding="UTF-8",
                standalone=True,
            )

        self.doc.save(output_path)
        logger.info("Saved redlined document to %s", output_path)
        return output_path
