"""English / Arabic strings for the results report (PDF and portal).

The report language follows the assessment's *Report Language* (or an explicit `language`
request parameter), not the desk user's language, so a client always receives the report in the
language they chose.
"""

LANGS = ("en", "ar")

LEVEL_NAMES = {
	"en": {"A": "Ad hoc", "B": "Foundational", "C": "Established", "D": "Leading", "N/A": "Not applicable"},
	"ar": {"A": "ارتجالي", "B": "تأسيسي", "C": "راسخ", "D": "رائد", "N/A": "لا ينطبق"},
}
LETTERS = {
	"en": {"A": "A", "B": "B", "C": "C", "D": "D", "N/A": "N/A"},
	"ar": {"A": "أ", "B": "ب", "C": "ج", "D": "د", "N/A": "–"},
}
PRIORITY = {
	"en": {"Immediate": ("Immediate", "0–3 months"), "High": ("High", "3–6 months"), "Medium": ("Medium", "6–12 months")},
	"ar": {"Immediate": ("فورية", "0–3 أشهر"), "High": ("مرتفعة", "3–6 أشهر"), "Medium": ("متوسطة", "6–12 شهراً")},
}

RESPONDENT_ROLES_AR = {
	"Chief Audit Executive": "الرئيس التنفيذي للتدقيق",
	"Audit Committee Member": "عضو لجنة المراجعة",
	"Board Member": "عضو مجلس الإدارة",
	"Executive Management": "الإدارة التنفيذية",
	"Internal Audit Staff": "موظفو التدقيق الداخلي",
	"Second Line (Risk / Compliance)": "الخط الثاني (المخاطر / الالتزام)",
	"External Consultant": "مستشار خارجي",
	"Other": "أخرى",
}
REVIEW_STATUS_AR = {
	"Pending Review": "قيد المراجعة",
	"Reviewed": "تمت المراجعة",
	"Approved": "معتمد",
	"Returned": "مُعاد للتصحيح",
}


def has_arabic(text):
	return any("\u0600" <= ch <= "\u06ff" or "\u0750" <= ch <= "\u077f" for ch in str(text or ""))


def bidi(text, lang):
	"""Keep Latin text (names, entity) in the right order inside an Arabic paragraph.

	Wraps it in LEFT-TO-RIGHT EMBEDDING ... POP DIRECTIONAL FORMATTING, which both browsers and
	wkhtmltopdf honour (newer isolate characters are not supported by wkhtmltopdf).
	"""
	text = str(text or "")
	if lang != "ar" or not text or has_arabic(text):
		return text
	return "\u202a" + text + "\u202c"


STRINGS = {
	"en": {
		"results_report": "Results report",
		"internal_report": "Internal report",
		"internal_banner": "INTERNAL – for {0} use only. Not for distribution to the client.",
		"title": "Internal Audit Function Maturity Assessment",
		"reference": "Reference",
		"assessment_date": "Assessment date",
		"assessed_by": "Assessed by",
		"perspective": "Perspective",
		"framework": "Framework",
		"framework_value": "IIA Global Internal Audit Standards",
		"questions": "Questions",
		"questions_value": "{0} across {1} sections",
		"review": "Review",
		"exec_summary": "Executive summary",
		"points_of": "{0} of {1} points",
		"strongest": "Strongest section",
		"weakest": "Weakest section",
		"findings_raised": "{0} findings raised, {1} requiring immediate action.",
		"na_marked": "{0} question(s) marked not applicable.",
		"results_by_section": "Results by section",
		"section": "Section",
		"points": "Points",
		"score": "Score",
		"maturity": "Maturity",
		"overall": "Overall",
		"key_findings": "Key findings",
		"area": "Area",
		"answer": "Answer",
		"current_practice": "Current practice",
		"priority": "Priority",
		"no_findings": "No findings: every question was answered at level C or above.",
		"roadmap": "Improvement roadmap",
		"target_practice": "Target practice (next level)",
		"owner": "Owner",
		"timeframe": "Timeframe",
		"no_actions": "No improvement actions required.",
		"detailed": "Detailed responses",
		"show_all": "Show all {0} answers",
		"question": "Question",
		"pts": "Pts",
		"comment": "Evidence / comment",
		"auto_calc": "Auto-calculated",
		"reviewer_comments": "Reviewer comments",
		"scoring_method": "Scoring method",
		"scoring_text": "Answers score A = {a}, B = {b}, C = {c}, D = {d} points. Section score = points ÷ (applicable "
		"questions × maximum points); questions marked not applicable are excluded. Maturity bands: {bands}. "
		"Findings are raised for answers at level A (Immediate, 0–3 months) or B (High, 3–6 months). Gating "
		"questions cap the overall maturity level when answered at the trigger level.",
		"benchmark": "Peer benchmark",
		"benchmark_note": "Compared with the latest submitted assessment of {0} other entities ({1}). Only "
		"aggregated, anonymous figures are shown. As at {2}.",
		"peer_all": "all entities",
		"peer_sector": "same sector: {0}",
		"your_score": "Your score",
		"peer_median": "Peer median",
		"peer_iqr": "Middle 50% of peers",
		"vs_median": "vs median",
		"percentile_text": "Higher than about {0}% of peer entities.",
		"benchmark_unavailable": "The peer benchmark is shown once at least {0} other entities have submitted an "
		"assessment, so that no individual entity can be identified.",
		"benchmark_no_sector": "The peer benchmark compares entities in the same sector, but no sector is recorded "
		"for this entity.",
		"confidential": "Confidential",
		"page": "Page",
		"of": "of",
		"you": "You",
	},
	"ar": {
		"results_report": "تقرير النتائج",
		"internal_report": "تقرير داخلي",
		"internal_banner": "تقرير داخلي – للاستخدام الداخلي لدى {0} فقط، ولا يُسلَّم للعميل.",
		"title": "تقييم نضج وظيفة التدقيق الداخلي",
		"reference": "المرجع",
		"assessment_date": "تاريخ التقييم",
		"assessed_by": "أُجري بواسطة",
		"perspective": "المنظور",
		"framework": "الإطار",
		"framework_value": "معايير التدقيق الداخلي العالمية (IIA)",
		"questions": "الأسئلة",
		"questions_value": "{0} سؤالاً في {1} أقسام",
		"review": "المراجعة",
		"exec_summary": "الملخص التنفيذي",
		"points_of": "{0} من أصل {1} نقطة",
		"strongest": "أقوى قسم",
		"weakest": "أضعف قسم",
		"findings_raised": "تم رصد {0} ملاحظة، منها {1} تتطلب إجراءً فورياً.",
		"na_marked": "عدد الأسئلة غير المنطبقة: {0}.",
		"results_by_section": "النتائج حسب القسم",
		"section": "القسم",
		"points": "النقاط",
		"score": "النتيجة",
		"maturity": "مستوى النضج",
		"overall": "الإجمالي",
		"key_findings": "أبرز الملاحظات",
		"area": "المجال",
		"answer": "الإجابة",
		"current_practice": "الممارسة الحالية",
		"priority": "الأولوية",
		"no_findings": "لا توجد ملاحظات: أُجيب عن جميع الأسئلة بالمستوى (ج) أو أعلى.",
		"roadmap": "خارطة طريق التحسين",
		"target_practice": "الممارسة المستهدفة (المستوى التالي)",
		"owner": "المسؤول",
		"timeframe": "الإطار الزمني",
		"no_actions": "لا توجد إجراءات تحسين مطلوبة.",
		"detailed": "تفاصيل الإجابات",
		"show_all": "عرض جميع الإجابات ({0})",
		"question": "السؤال",
		"pts": "النقاط",
		"comment": "الأدلة / التعليق",
		"auto_calc": "محسوبة تلقائياً",
		"reviewer_comments": "ملاحظات المراجِع",
		"scoring_method": "منهجية التقييم",
		"scoring_text": "تُمنح الإجابات النقاط التالية: أ = {a}، ب = {b}، ج = {c}، د = {d}. نتيجة القسم = النقاط ÷ (عدد الأسئلة "
		"المنطبقة × الحد الأقصى للنقاط)، وتُستبعد الأسئلة غير المنطبقة. نطاقات النضج: {bands}. تُرصد الملاحظات "
		"للإجابات في المستوى (أ) بأولوية فورية خلال 0–3 أشهر، والمستوى (ب) بأولوية مرتفعة خلال 3–6 أشهر. "
		"وتحدّ الأسئلة الحاكمة من مستوى النضج العام عند الإجابة عنها بالمستوى المحدد.",
		"benchmark": "المقارنة مع النظراء",
		"benchmark_note": "مقارنة بآخر تقييم مُعتمد لعدد {0} من الجهات الأخرى ({1}). تُعرض أرقام مجمّعة وغير "
		"معرِّفة فقط. كما في {2}.",
		"peer_all": "جميع الجهات",
		"peer_sector": "القطاع نفسه: {0}",
		"your_score": "نتيجتكم",
		"peer_median": "وسيط النظراء",
		"peer_iqr": "النطاق الأوسط (50%) للنظراء",
		"vs_median": "مقارنة بالوسيط",
		"percentile_text": "أعلى من نحو {0}% من الجهات المماثلة.",
		"benchmark_unavailable": "تظهر المقارنة مع النظراء عندما تُقدّم {0} جهات أخرى على الأقل تقييماتها، "
		"حتى لا يمكن التعرف على أي جهة بعينها.",
		"benchmark_no_sector": "تقارن المقارنة الجهات في القطاع نفسه، لكن لم يُسجَّل قطاع لهذه الجهة.",
		"confidential": "سري",
		"page": "صفحة",
		"of": "من",
		"you": "أنتم",
	},
}


def norm_lang(lang):
	lang = (lang or "en").lower()[:2]
	return lang if lang in LANGS else "en"


def strings(lang):
	return STRINGS[norm_lang(lang)]
