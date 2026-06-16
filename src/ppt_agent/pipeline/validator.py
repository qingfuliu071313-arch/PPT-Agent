"""Content validator: checks data structure integrity before rendering — image-first rules."""

from __future__ import annotations

from ppt_agent.models import Presentation, SlideContent, SlideLayout


class ValidationError:
    def __init__(self, slide_index: int, field: str, message: str, auto_fixed: bool = False):
        self.slide_index = slide_index
        self.field = field
        self.message = message
        self.auto_fixed = auto_fixed

    def __str__(self) -> str:
        tag = "[auto-fixed]" if self.auto_fixed else "[ERROR]"
        return f"Slide {self.slide_index} | {self.field}: {tag} {self.message}"


IMAGE_LAYOUTS = {SlideLayout.IMAGE_FOCUS, SlideLayout.DUAL_IMAGE, SlideLayout.FIGURE_CAPTION}


class ContentValidator:

    def validate(self, presentation: Presentation) -> list[ValidationError]:
        errors: list[ValidationError] = []
        for slide in presentation.slides:
            errors.extend(self._validate_slide(slide))
        return errors

    def validate_and_fix(self, presentation: Presentation) -> list[ValidationError]:
        errors: list[ValidationError] = []
        for slide in presentation.slides:
            errors.extend(self._validate_and_fix_slide(slide))
        return errors

    def _validate_slide(self, s: SlideContent) -> list[ValidationError]:
        errs: list[ValidationError] = []
        idx = s.index

        if not s.title.strip():
            errs.append(ValidationError(idx, "title", "Title is empty"))

        if s.layout in IMAGE_LAYOUTS and not s.images and not s.left_image and not s.right_image:
            errs.append(ValidationError(idx, "images", f"{s.layout.value} slide has no image specs"))

        if s.layout not in (SlideLayout.TITLE, SlideLayout.SECTION, SlideLayout.CLOSING,
                            SlideLayout.REFERENCES) and not s.key_statement:
            errs.append(ValidationError(idx, "key_statement", "Missing key statement"))

        if s.layout != SlideLayout.TEXT_BLOCK and len(s.annotations) > 5:
            errs.append(ValidationError(idx, "annotations", f"Too many annotations ({len(s.annotations)}), max 5"))

        dispatch = {
            SlideLayout.CHART: self._check_chart,
            SlideLayout.PROCESS_FLOW: self._check_process,
            SlideLayout.TABLE: self._check_table,
            SlideLayout.KEY_FINDINGS: self._check_metrics,
            SlideLayout.DUAL_IMAGE: self._check_dual_image,
        }
        checker = dispatch.get(s.layout)
        if checker:
            errs.extend(checker(s))

        return errs

    def _validate_and_fix_slide(self, s: SlideContent) -> list[ValidationError]:
        errs: list[ValidationError] = []
        idx = s.index

        if not s.title.strip():
            s.title = f"Slide {idx}"
            errs.append(ValidationError(idx, "title", "Title was empty, set to default", auto_fixed=True))

        if s.layout not in (SlideLayout.TITLE, SlideLayout.SECTION, SlideLayout.CLOSING,
                            SlideLayout.REFERENCES) and not s.key_statement:
            s.key_statement = s.title
            errs.append(ValidationError(idx, "key_statement", "Used title as key statement fallback", auto_fixed=True))

        if s.layout != SlideLayout.TEXT_BLOCK and len(s.annotations) > 5:
            s.annotations = s.annotations[:5]
            errs.append(ValidationError(idx, "annotations", "Truncated to 5 annotations", auto_fixed=True))

        dispatch = {
            SlideLayout.CHART: self._fix_chart,
            SlideLayout.PROCESS_FLOW: self._fix_process,
            SlideLayout.TABLE: self._fix_table,
            SlideLayout.KEY_FINDINGS: self._fix_metrics,
        }
        fixer = dispatch.get(s.layout)
        if fixer:
            errs.extend(fixer(s))

        return errs

    # ── Check-only methods ──────────────────────────────────────

    def _check_dual_image(self, s: SlideContent) -> list[ValidationError]:
        errs = []
        has_left = s.left_image or (len(s.images) > 0)
        has_right = s.right_image or (len(s.images) > 1)
        if not has_left or not has_right:
            errs.append(ValidationError(s.index, "images", "Dual image slide needs 2 images"))
        return errs

    def _check_chart(self, s: SlideContent) -> list[ValidationError]:
        errs = []
        if not s.chart_data:
            errs.append(ValidationError(s.index, "chart_data", "Chart slide has no chart_data"))
            return errs
        cd = s.chart_data
        if not cd.categories:
            errs.append(ValidationError(s.index, "categories", "Chart has no categories"))
        if not cd.series:
            errs.append(ValidationError(s.index, "series", "Chart has no series"))
        for i, ser in enumerate(cd.series):
            vals = ser.get("values", [])
            if len(vals) != len(cd.categories):
                errs.append(ValidationError(
                    s.index, f"series[{i}]",
                    f"Series '{ser.get('name', i)}' has {len(vals)} values but {len(cd.categories)} categories"
                ))
        return errs

    def _check_process(self, s: SlideContent) -> list[ValidationError]:
        errs = []
        if not s.process_steps:
            errs.append(ValidationError(s.index, "process_steps", "Process slide has no steps"))
        elif not 2 <= len(s.process_steps) <= 8:
            errs.append(ValidationError(s.index, "process_steps", f"Steps count {len(s.process_steps)}, recommend 3-6"))
        return errs

    def _check_table(self, s: SlideContent) -> list[ValidationError]:
        errs = []
        if not s.table_data:
            errs.append(ValidationError(s.index, "table_data", "Table slide has no data"))
            return errs
        if len(s.table_data) < 2:
            errs.append(ValidationError(s.index, "table_data", "Table needs at least header + 1 data row"))
        col_count = len(s.table_data[0]) if s.table_data else 0
        for i, row in enumerate(s.table_data[1:], 1):
            if len(row) != col_count:
                errs.append(ValidationError(
                    s.index, f"table_data[{i}]",
                    f"Row has {len(row)} columns, header has {col_count}"
                ))
        return errs

    def _check_metrics(self, s: SlideContent) -> list[ValidationError]:
        errs = []
        if not s.metrics:
            errs.append(ValidationError(s.index, "metrics", "Key findings slide has no metrics"))
        elif not 1 <= len(s.metrics) <= 6:
            errs.append(ValidationError(s.index, "metrics", f"Metrics count {len(s.metrics)}, recommend 2-4"))
        else:
            for i, m in enumerate(s.metrics):
                if not isinstance(m, dict):
                    errs.append(ValidationError(s.index, f"metrics[{i}]", "Metric is not a dict"))
                elif not m.get("value") or not m.get("label"):
                    errs.append(ValidationError(s.index, f"metrics[{i}]", "Missing value or label"))
        return errs

    # ── Fix methods ────────────────────────────────────────────

    def _fix_chart(self, s: SlideContent) -> list[ValidationError]:
        errs = self._check_chart(s)
        if s.chart_data and s.chart_data.series:
            cat_len = len(s.chart_data.categories)
            fixed_any = False
            for ser in s.chart_data.series:
                vals = ser.get("values", [])
                if len(vals) > cat_len:
                    ser["values"] = vals[:cat_len]
                    fixed_any = True
                elif len(vals) < cat_len:
                    ser["values"] = vals + [0] * (cat_len - len(vals))
                    fixed_any = True
            if fixed_any:
                errs = [e for e in errs if "values" not in e.field]
                errs.append(ValidationError(s.index, "series", "Padded/trimmed series to match categories", auto_fixed=True))
        return errs

    def _fix_process(self, s: SlideContent) -> list[ValidationError]:
        errs = []
        if not s.process_steps:
            from ppt_agent.models import ProcessStep
            s.process_steps = [ProcessStep(label=f"步骤{i+1}") for i in range(3)]
            errs.append(ValidationError(s.index, "process_steps", "No steps, set placeholder", auto_fixed=True))
        return errs

    def _fix_table(self, s: SlideContent) -> list[ValidationError]:
        errs = []
        if not s.table_data:
            errs.append(ValidationError(s.index, "table_data", "No table data, cannot auto-fix"))
            return errs
        col_count = len(s.table_data[0])
        for i, row in enumerate(s.table_data[1:], 1):
            if len(row) < col_count:
                s.table_data[i] = row + [""] * (col_count - len(row))
                errs.append(ValidationError(s.index, f"table_data[{i}]", "Padded missing columns", auto_fixed=True))
            elif len(row) > col_count:
                s.table_data[i] = row[:col_count]
                errs.append(ValidationError(s.index, f"table_data[{i}]", "Trimmed extra columns", auto_fixed=True))
        return errs

    def _fix_metrics(self, s: SlideContent) -> list[ValidationError]:
        errs = []
        if not s.metrics:
            errs.append(ValidationError(s.index, "metrics", "No metrics, cannot auto-fix"))
        else:
            for i, m in enumerate(s.metrics):
                if isinstance(m, dict):
                    if not m.get("value"):
                        m["value"] = "N/A"
                        errs.append(ValidationError(s.index, f"metrics[{i}]", "Missing value, set N/A", auto_fixed=True))
                    if not m.get("label"):
                        m["label"] = f"指标{i + 1}"
                        errs.append(ValidationError(s.index, f"metrics[{i}]", "Missing label, set default", auto_fixed=True))
        return errs
