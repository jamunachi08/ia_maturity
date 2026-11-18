// Page tour content is deliberately local to the frontend: it never changes user data.
export type TourStep = { selector?: string; optional?: boolean; en: [string, string]; ar: [string, string] };
const step = (
  selector: string | undefined,
  en: [string, string],
  ar: [string, string],
  optional = false,
): TourStep => ({ selector, en, ar, optional });
const title = (en: string, ar: string, body: string, bodyAr: string) =>
  step(
    ".main-content .page-title, .main-content .onboarding, .main-content .guide-hero",
    [en, body],
    [ar, bodyAr],
  );
const search = step(
  ".main-content .toolbar",
  [
    "Find records",
    "Search or filter the list to narrow the results. For example, search for an organization name, then open the matching row. Filters affect the list, not the underlying records.",
  ],
  [
    "البحث عن السجلات",
    "استخدم البحث أو المرشحات لتضييق النتائج. مثلاً ابحث عن اسم منظمة ثم افتح الصف المطابق. تؤثر المرشحات في القائمة فقط ولا تغير السجلات.",
  ],
  true,
);
const rows = step(
  ".main-content .table-scroll, .main-content .empty",
  [
    "Open a record",
    "Review the list and choose Open or the record name for more details. If the list is empty, check your filters and access; some features require an assignment.",
  ],
  [
    "فتح سجل",
    "راجع القائمة واختر فتح أو اسم السجل لعرض التفاصيل. إذا كانت القائمة فارغة فتحقق من المرشحات والصلاحيات؛ تتطلب بعض الميزات إسناداً.",
  ],
  true,
);
const actions = step(
  ".main-content .page-title-actions",
  [
    "Available actions",
    "Use the actions here to create or start work when your role permits it. Buttons may be absent or disabled until prerequisites are met.",
  ],
  [
    "الإجراءات المتاحة",
    "استخدم الأزرار هنا لإنشاء العمل أو بدئه عندما يسمح دورك. قد تختفي الأزرار أو تتعطل إلى حين استيفاء المتطلبات.",
  ],
  true,
);
const overview: TourStep[] = [
  title(
    "Your workspace",
    "مساحة عملك",
    "This is your starting point after sign-in. The content reflects your role, organization and assignments. This tour is shown once per page in this browser; use Take page tour to replay it.",
    "هذه نقطة البداية بعد تسجيل الدخول. يعكس المحتوى دورك ومنظمتك وإسناداتك. تظهر الجولة مرة لكل صفحة في هذا المتصفح؛ استخدم جولة الصفحة لإعادتها.",
  ),
  step(
    ".sidebar nav, .mobile-toggle",
    [
      "Navigation",
      "Use the sidebar to open assessments, organizations or customers, actions and activity. On a small screen, open the menu first. Administrators also see the Administration section.",
    ],
    [
      "التنقل",
      "استخدم القائمة لفتح التقييمات والمنظمات أو العملاء والإجراءات والنشاط. على الشاشة الصغيرة افتح القائمة أولاً. يرى المدير أيضاً قسم الإدارة.",
    ],
  ),
  step(
    ".topbar-controls",
    [
      "Organization, language and help",
      "Choose an organization when the selector is available. Switch between العربية and English, open Help & guides, or replay this page tour from the header.",
    ],
    [
      "المنظمة واللغة والمساعدة",
      "اختر المنظمة عند توفر المحدد. بدّل بين العربية وEnglish أو افتح المساعدة والأدلة أو أعد جولة الصفحة من الشريط العلوي.",
    ],
  ),
  step(
    ".stat-grid",
    [
      "Overview cards",
      "Select a card to open the related records. For example, Awaiting review shows assessments that need review; Overdue helps identify work past its deadline.",
    ],
    [
      "بطاقات النظرة العامة",
      "اختر بطاقة لفتح السجلات المرتبطة. مثلاً تعرض بانتظار المراجعة التقييمات التي تحتاج مراجعة، وتساعدك متأخر على معرفة العمل المتجاوز لموعده.",
    ],
    true,
  ),
  step(
    ".next-action, .onboarding",
    [
      "Your next step",
      "Continue an existing assessment here. If you are setting up a new organization, provide its name, sector and contact email. To join an existing organization, request an invitation instead of creating a duplicate.",
    ],
    [
      "خطوتك التالية",
      "تابع التقييم الحالي من هنا. إذا كنت تهيئ منظمة جديدة فأدخل اسمها وقطاعها وبريد التواصل. للانضمام لمنظمة موجودة اطلب دعوة بدلاً من إنشاء نسخة مكررة.",
    ],
    true,
  ),
  step(
    '[data-testid="staff-getting-started"]',
    [
      "Getting started is optional",
      "Read the next steps for your staff role. A new account can have no assigned customers yet. Close this guidance or skip this tour whenever you want; no organization or assessment selection is required to enter the workspace.",
    ],
    [
      "إرشادات البدء اختيارية",
      "اقرأ الخطوات المناسبة لدورك. قد لا توجد عملاء مسندون للحساب الجديد. أغلق الإرشادات أو تخطّ الجولة متى شئت؛ لا يلزم اختيار منظمة أو تقييم للدخول إلى مساحة العمل.",
    ],
    true,
  ),
  actions,
  search,
  rows,
  step(
    ".sidebar-bottom",
    [
      "Your account",
      "Open your profile to manage permitted personal details, password and authenticator. Use the sign-out icon when finished.",
    ],
    [
      "حسابك",
      "افتح ملفك الشخصي لإدارة البيانات المسموح بها وكلمة المرور وتطبيق المصادقة. استخدم رمز الخروج عند الانتهاء.",
    ],
    true,
  ),
];
const assessment: TourStep[] = [
  title(
    "Assessment and status",
    "التقييم والحالة",
    "The heading identifies the organization and assessment. The status determines what you can do: a submitted assessment is locked until clarification is requested.",
    "يحدد العنوان المنظمة والتقييم. تحدد الحالة الإجراءات المتاحة: يُقفل التقييم المرسل حتى يُطلب توضيح.",
  ),
  step(
    ".iam-stepper",
    [
      "Sections",
      "Choose a section to move between topics. Completed sections are marked; you can return to earlier sections while the assessment is editable.",
    ],
    [
      "الأقسام",
      "اختر قسماً للتنقل بين الموضوعات. تُعلّم الأقسام المكتملة ويمكن العودة للأقسام السابقة ما دام التقييم قابلاً للتعديل.",
    ],
    true,
  ),
  step(
    ".iam-progress-row",
    [
      "Progress and live score",
      "The counter shows answered questions. Where available, the live score is preliminary and can change as answers change; it is not an approved report.",
    ],
    [
      "التقدم والنتيجة المباشرة",
      "يعرض العداد الأسئلة المجاب عنها. عند ظهور النتيجة المباشرة فهي أولية وتتغير مع الإجابات وليست تقريراً معتمداً.",
    ],
    true,
  ),
  step(
    ".question-card",
    [
      "Answer a question",
      "Read the question and guidance, then choose the option that best describes the current practice. For example, select the option describing a documented process only when that practice exists. Some questions allow multiple choices or Not applicable.",
    ],
    [
      "الإجابة عن سؤال",
      "اقرأ السؤال والإرشادات ثم اختر الوصف الأقرب للممارسة الحالية. مثلاً اختر وصف العملية الموثقة فقط عند وجود هذه الممارسة. تسمح بعض الأسئلة بأكثر من اختيار أو غير منطبق.",
    ],
    true,
  ),
  step(
    ".question-card .iam-comment, .question-card .evidence-row",
    [
      "Explain and support answers",
      "Where enabled, add a comment and attach evidence, such as an approved policy. Evidence and comments depend on questionnaire settings and your access.",
    ],
    [
      "توضيح الإجابات ودعمها",
      "عند الإتاحة أضف تعليقاً وأرفق دليلاً مثل سياسة معتمدة. تعتمد الأدلة والتعليقات على إعدادات الاستبيان وصلاحيتك.",
    ],
    true,
  ),
  step(
    ".editor-footer",
    [
      "Save, navigate and submit",
      "Answers save as you work; the Save button is also available. Use Next section to continue. On the final section, submit once all required questions are answered. Submission locks answers for review.",
    ],
    [
      "الحفظ والتنقل والإرسال",
      "تُحفظ الإجابات أثناء العمل ويتوفر زر حفظ أيضاً. استخدم القسم التالي للمتابعة. في القسم الأخير أرسل بعد إجابة جميع الأسئلة المطلوبة. يؤدي الإرسال إلى قفل الإجابات للمراجعة.",
    ],
    true,
  ),
  step(
    ".review-actions",
    [
      "Review decisions",
      "When assigned and authorized, begin review, request clarification, approve or release the report as the state permits. For example, explain a missing document when requesting clarification.",
    ],
    [
      "قرارات المراجعة",
      "عند إسنادك وتفويضك يمكنك بدء المراجعة أو طلب توضيح أو الاعتماد أو إصدار التقرير حسب الحالة. مثلاً وضّح المستند الناقص عند طلب توضيح.",
    ],
    true,
  ),
  step(
    ".scorecard, .report-delivery",
    [
      "Results and report",
      "Scores may be preliminary. The approved report requires release, and download or email availability follows the administrator’s policy.",
    ],
    [
      "النتائج والتقرير",
      "قد تكون النتائج أولية. يتطلب التقرير المعتمد إصداره، ويعتمد التنزيل أو الإرسال بالبريد على سياسة المدير.",
    ],
    true,
  ),
];
const pageTours: Record<string, TourStep[]> = {
  customerDates: [
    title(
      "Assessment dates",
      "تواريخ التقييم",
      "See when your assessments started and when you submitted them. Detailed change history is retained for staff.",
      "اطلع على موعد بدء تقييماتك وإرسالها. يُحتفظ بسجل التغييرات التفصيلي للموظفين.",
    ),
  ],
  auditPackages: [
    title(
      "Audit packages",
      "حزم التدقيق",
      "Choose a published questionnaire version to configure the choices offered to future customers.",
      "اختر إصدار استبيان منشوراً لضبط الخيارات المعروضة للعملاء الجدد.",
    ),
    step(
      '[data-tour="required-sections"]',
      [
        "Required sections",
        "Keep essential sections always included. Required sections alone are a valid scope when they contain questions.",
      ],
      [
        "الأقسام الإلزامية",
        "أبقِ الأقسام الأساسية مشمولة دائماً. تكفي الأقسام الإلزامية وحدها عندما تتضمن أسئلة.",
      ],
      true,
    ),
    step(
      '[data-tour="package-editor"]',
      [
        "Explain each choice",
        "Give each package a stable code, clear English and Arabic labels and descriptions, and select its sections. Customers may combine packages; overlapping sections count once.",
      ],
      [
        "توضيح كل خيار",
        "أدخل رمزاً ثابتاً واسم ووصفاً واضحين بالإنجليزية والعربية وحدد الأقسام. يمكن للعميل جمع الحزم، وتُحتسب الأقسام المشتركة مرة واحدة.",
      ],
      true,
    ),
    step(
      '[data-tour="package-preview"]',
      [
        "Preview the scope",
        "Try package combinations here. The question count reflects the union of selected and required sections. This preview creates no assessment.",
      ],
      [
        "معاينة النطاق",
        "جرّب جمع الحزم هنا. يعكس عدد الأسئلة اتحاد الأقسام المختارة والإلزامية. لا تنشئ المعاينة تقييماً.",
      ],
      true,
    ),
    step(
      '[data-tour="publish-packages"]',
      [
        "Save and publish",
        "Save a draft while preparing. Publish when ready. Published versions are immutable; later edits create a new version for future assessments.",
      ],
      [
        "الحفظ والنشر",
        "احفظ مسودة أثناء الإعداد ثم انشر عند الجاهزية. الإصدارات المنشورة ثابتة، وتنتج التعديلات اللاحقة إصداراً جديداً للتقييمات المستقبلية.",
      ],
      true,
    ),
  ],
  assessmentScope: [
    title(
      "Choose your audit scope",
      "اختر نطاق التدقيق",
      "Review the package descriptions before answering. Your choices determine the questions, progress and scoring in your assessment and report.",
      "راجع أوصاف الحزم قبل الإجابة. تحدد اختياراتك الأسئلة والتقدم والنتائج في التقييم والتقرير.",
    ),
    step(
      '[data-tour="scope-choices"]',
      [
        "Combine packages",
        "Select the topics you want assessed. Required sections remain included and shared questions count once. Excluded sections appear as Not assessed, without a zero score.",
      ],
      [
        "الجمع بين الحزم",
        "اختر المواضيع المطلوب تقييمها. تبقى الأقسام الإلزامية مشمولة وتُحتسب الأسئلة المشتركة مرة واحدة. تظهر الأقسام المستبعدة بعبارة لم يُقيّم دون نتيجة صفرية.",
      ],
    ),
    step(
      '[data-tour="confirm-scope"]',
      [
        "Confirm before answering",
        "Confirm when satisfied. Only an administrator can correct an unsubmitted draft, with a recorded reason and your acknowledgement. Submitted scope cannot change.",
      ],
      [
        "التأكيد قبل الإجابة",
        "أكد عند الانتهاء. وحده المسؤول يصحح نطاق مسودة غير مرسلة مع تسجيل السبب وطلب إقرارك. لا يتغير النطاق بعد الإرسال.",
      ],
      true,
    ),
  ],
  onboarding: [
    title(
      "Customer onboarding",
      "تسجيل العملاء",
      "Track your invitations even before you have assigned customers. Only you and GRC administrators can inspect your pending invitations.",
      "تابع دعواتك حتى قبل إسناد العملاء إليك. لا يطّلع على دعواتك المعلقة سوى أنت ومسؤولي GRC.",
    ),
    step(
      '[data-tour="invite-customer"]',
      [
        "Invite the intended customer",
        "Choose Invite customer, enter their email and language, then send when ready. The server permanently records you as the original inviter. The tour never sends a message.",
      ],
      [
        "دعوة العميل المقصود",
        "اختر دعوة عميل وأدخل البريد واللغة ثم أرسل عند الجاهزية. يسجل الخادم هويتك كصاحب الدعوة الأصلي. لا ترسل الجولة أي رسالة.",
      ],
      true,
    ),
    step(
      '[data-tour="onboarding-tracker"]',
      [
        "Find the next action",
        "Filter by status or Needs attention and open an invitation. Progress comes from completed server milestones; mail status does not prove delivery or reading.",
      ],
      [
        "تحديد الخطوة التالية",
        "رشّح حسب الحالة أو بحاجة إلى متابعة وافتح الدعوة. يعكس التقدم مراحل مكتملة على الخادم، ولا تثبت حالة البريد وصول الرسالة أو قراءتها.",
      ],
      true,
    ),
    step(
      '[data-tour="customer-onboarding"]',
      [
        "Resume securely",
        "Resume your email-matched invitation, verify if requested, and submit your organization details. Existing organizations require an authorized membership invitation.",
      ],
      [
        "المتابعة بأمان",
        "استأنف الدعوة المطابقة لبريدك وأكمل التحقق عند الطلب ثم أرسل بيانات منظمتك. تتطلب المنظمات الموجودة دعوة عضوية مخولة.",
      ],
      true,
    ),
  ],
  onboardingDetail: [
    title(
      "Invitation progress",
      "تقدم الدعوة",
      "Review the original inviter, expiry and last meaningful activity. Completed steps survive resends and another-browser sign-in.",
      "راجع صاحب الدعوة الأصلي والصلاحية وآخر نشاط فعلي. تُحفظ المراحل المكتملة بعد إعادة الإرسال وتسجيل الدخول من متصفح آخر.",
    ),
    step(
      '[data-tour="onboarding-progress"]',
      [
        "Milestones and blockers",
        "The next action identifies the customer or approver who must act. Unfinished profile values are private. Completed onboarding links the customer to the original auditor.",
      ],
      [
        "المراحل والعوائق",
        "تحدد الخطوة التالية العميل أو المعتمد المطلوب منه الإجراء. تبقى بيانات الملف غير المكتملة خاصة. يربط اكتمال التسجيل العميل بالمدقق الأصلي.",
      ],
    ),
    step(
      '[data-tour="onboarding-actions"]',
      [
        "Follow up manually",
        "Send a reminder or resend to issue a fresh link; the previous link stops working. Revoke requires a reason. These buttons are available only when permitted.",
      ],
      [
        "المتابعة اليدوية",
        "أرسل تذكيراً أو أعد الإرسال لإصدار رابط جديد وإبطال السابق. يتطلب الإلغاء سبباً. تظهر الإجراءات وفق الصلاحية.",
      ],
      true,
    ),
    step(
      '[data-tour="onboarding-history"]',
      [
        "Review the timeline",
        "Use recorded events and timestamps to understand progress. Page visits and email scanners do not complete milestones.",
      ],
      [
        "مراجعة التسلسل الزمني",
        "استعن بالأحداث المسجلة وأوقاتها لفهم التقدم. لا تُكمل زيارات الصفحة أو ماسحات البريد مراحل التسجيل.",
      ],
    ),
  ],
  onboardingControls: [
    title(
      "Onboarding defaults",
      "افتراضات التسجيل",
      "These controls are available to GRC administrators. Every change requires a reason.",
      "هذه الأدوات متاحة لمسؤولي GRC. يتطلب كل تغيير سبباً.",
    ),
    step(
      '[data-tour="onboarding-controls"]',
      [
        "Lock and attention policy",
        "Auto-lock is saved with each new invitation and does not change existing customers. Needs attention defaults to 48 hours without customer progress. Approval waiting names the approver instead.",
      ],
      [
        "سياسة القفل والمتابعة",
        "يُحفظ القفل التلقائي مع كل دعوة جديدة ولا يغير العملاء الحاليين. تبدأ الحاجة للمتابعة افتراضياً بعد 48 ساعة دون تقدم العميل. يحدد انتظار الاعتماد الجهة المعتمدة بدلاً من ذلك.",
      ],
    ),
  ],
  oversight: [
    title(
      "Customer and auditor overview",
      "نظرة عامة على العملاء والمدققين",
      "Administrators see all customers and auditors. Managers see customers where they hold an active Manager assignment. Open a customer or auditor to inspect profiles and work reports.",
      "يرى المسؤول جميع العملاء والمدققين. يرى المدير العملاء الذين يحمل لديهم إسناد مدير نشطاً. افتح العميل أو المدقق للاطلاع على الملف وتقارير العمل.",
    ),
    step(
      ".oversight-metrics",
      [
        "Portfolio totals",
        "These cards count the customers, auditors, active assignments and pending approvals you can access. Pending requests have not changed access yet.",
      ],
      [
        "إجماليات المحفظة",
        "تعرض البطاقات أعداد العملاء والمدققين والإسنادات النشطة والاعتمادات المعلقة المسموح لك بها. لم تغير الطلبات المعلقة الوصول بعد.",
      ],
    ),
    step(
      ".oversight-tabs",
      [
        "Profiles and reports",
        "Use Customers, Auditors and Approvals to switch lists. View overview opens profile, assessment, action, follow-up and activity reports. Search each report and export it to CSV. For example, export a customer activity report for a management review.",
      ],
      [
        "الملفات والتقارير",
        "تنقل بين العملاء والمدققين والاعتمادات. يفتح عرض النظرة العامة الملف وتقارير التقييمات والإجراءات والمتابعات والنشاط. ابحث في التقرير وصدره إلى CSV. مثال: صدّر نشاط عميل لمراجعة الإدارة.",
      ],
    ),
    step(
      ".page-title-actions",
      [
        "Workflow controls",
        "Administrators set the global workflow. Each customer has a Workflow button for its managers and administrators. Enable onboarding or assignment approval and order the stages. For example, Manager then App administrator. Requests retain these stages after submission; self approval is disabled by default.",
      ],
      [
        "أدوات مسار الاعتماد",
        "يضبط المسؤول المسار العام. لكل عميل زر مسار الاعتماد لمديريه والمسؤولين. فعّل اعتماد التسجيل أو الإسناد ورتب الخطوات. مثال: المدير ثم مسؤول التطبيق. تحتفظ الطلبات بالخطوات بعد الإرسال ويُعطل الاعتماد الذاتي افتراضياً.",
      ],
    ),
    step(
      ".table-scroll",
      [
        "Review requests",
        "Open Approvals, then Review request to inspect the proposed values and approval history. Approve advances one stage; final approval applies the change. Reject or cancel requires a reason. A manager can request auditor onboarding for an assigned customer without gaining administrator account permissions.",
      ],
      [
        "مراجعة الطلبات",
        "افتح الاعتمادات ثم مراجعة الطلب لفحص القيم المقترحة وسجل الموافقات. تنقل الموافقة إلى الخطوة التالية ويطبق الاعتماد النهائي التغيير. يتطلب الرفض أو الإلغاء سبباً. يستطيع المدير طلب تسجيل مدقق لعميل مسند دون الحصول على صلاحيات حساب المسؤول.",
      ],
    ),
  ],
  overview,
  assessments: [
    title(
      "Assessments",
      "التقييمات",
      "Find existing assessments or start one when authorized. Each row shows its state, progress, deadline and owner.",
      "ابحث عن التقييمات أو ابدأ تقييماً عند السماح. يوضح كل صف الحالة والتقدم والموعد والمسؤول.",
    ),
    actions,
    search,
    rows,
    step(
      ".main-content .pagination",
      ["More results", "Use the page controls to move through longer lists."],
      ["المزيد من النتائج", "استخدم أدوات الصفحات للتنقل في القوائم الطويلة."],
      true,
    ),
  ],
  assessment,
  scorecards: [
    title(
      "Scorecards",
      "بطاقات النتائج",
      "Find available assessment results and reports. Visibility depends on review state and the administrator’s report policy.",
      "ابحث عن النتائج والتقارير المتاحة. يعتمد ظهورها على حالة المراجعة وسياسة التقارير لدى المدير.",
    ),
    search,
    rows,
  ],
  organizations: [
    title(
      "Organizations and customers",
      "المنظمات والعملاء",
      "Open a listed organization to see its details. Customers see organizations they belong to; staff see customers assigned to them.",
      "افتح منظمة من القائمة لعرض تفاصيلها. يرى العميل المنظمات التي ينتمي إليها ويرى الفريق العملاء المسندين إليه.",
    ),
    actions,
    search,
    rows,
  ],
  organization: [
    step(
      '[data-tour="customer-ownership"]',
      [
        "Ownership controls",
        "Administrators can transfer ownership, lock or unlock staff access, and grant named responsibility exceptions. A reason is required; transfers remove the former owner unless explicitly retained.",
      ],
      [
        "أدوات الملكية",
        "يمكن للمسؤول نقل الملكية وقفل وصول الفريق أو فتحه ومنح استثناءات مسماة بمسؤوليات محددة. يلزم سبب؛ ويُزال وصول المالك السابق ما لم يُحتفظ به صراحة.",
      ],
      true,
    ),
    title(
      "Organization details",
      "تفاصيل المنظمة",
      "This page collects organization information and access-related records. Some fields are read-only depending on your membership.",
      "تجمع هذه الصفحة بيانات المنظمة والسجلات المتعلقة بالوصول. تكون بعض الحقول للقراءة فقط حسب عضويتك.",
    ),
    step(
      ".main-content .tabs",
      [
        "Choose a tab",
        "Switch between profile, departments and branches, members, invitations and audit issues when available. For example, open Invitations to invite a contributor.",
      ],
      [
        "اختر علامة تبويب",
        "تنقل بين الملف والأقسام والفروع والأعضاء والدعوات وملاحظات التدقيق حسب المتاح. مثلاً افتح الدعوات لدعوة مساهم.",
      ],
      true,
    ),
    step(
      ".main-content .panel.padded",
      [
        "Update the profile",
        "Authorized organization administrators can update contact details and optional email preferences, then save changes.",
      ],
      [
        "تحديث الملف",
        "يمكن لمديري المنظمة المخولين تحديث بيانات الاتصال وتفضيلات البريد الاختيارية ثم حفظ التغييرات.",
      ],
      true,
    ),
    actions,
  ],
  actions: [
    title(
      "Improvement actions",
      "إجراءات التحسين",
      "Track the work arising from an assessment, including owner, due date and status.",
      "تابع الأعمال الناتجة عن التقييم بما فيها المسؤول والموعد والحالة.",
    ),
    search,
    rows,
    step(
      ".main-content .table-scroll",
      [
        "Update an action",
        "Open a row to review the recommendation. If authorized, update progress, add completion notes and evidence, then save. For example, attach an approved procedure before requesting verification.",
      ],
      [
        "تحديث إجراء",
        "افتح الصف لمراجعة التوصية. عند السماح حدّث الحالة وأضف ملاحظات الإنجاز والأدلة ثم احفظ. مثلاً أرفق إجراءً معتمداً قبل طلب التحقق.",
      ],
      true,
    ),
  ],
  activity: [
    title(
      "Activity",
      "النشاط",
      "Review a traceable history of authorized changes and assessment events.",
      "راجع سجلاً قابلاً للتتبع للتغييرات المصرح بها وأحداث التقييم.",
    ),
    step(
      ".main-content .toolbar",
      [
        "Filter organization",
        "Select an organization to narrow the timeline. All organizations shows records you are authorized to view.",
      ],
      ["تصفية المنظمة", "اختر منظمة لتضييق السجل. يعرض خيار كل المنظمات السجلات المصرح لك برؤيتها."],
      true,
    ),
    step(
      ".timeline, .main-content .empty",
      [
        "Read the timeline",
        "Each entry shows the event and its actor and time; open Details or an assessment link when provided.",
      ],
      ["قراءة السجل", "يعرض كل حدث الإجراء ومن نفذه ووقته؛ افتح التفاصيل أو رابط التقييم عند توفره."],
      true,
    ),
  ],
  followups: [
    title(
      "Customer follow-ups",
      "متابعات العملاء",
      "Record contact, next steps and deadlines for assigned customers.",
      "سجّل التواصل والخطوات التالية والمواعيد للعملاء المسندين.",
    ),
    actions,
    search,
    rows,
    step(
      ".main-content .page-title-actions",
      [
        "Add a follow-up",
        "Choose Add follow-up, select the organization, write a note and set an owner and optional due date. For example: “Confirm receipt of evidence by next week.”",
      ],
      [
        "إضافة متابعة",
        "اختر إضافة متابعة وحدد المنظمة واكتب ملاحظة وحدد المسؤول والموعد إن لزم. مثلاً: «تأكيد استلام الأدلة الأسبوع القادم».",
      ],
      true,
    ),
  ],
  preferences: [
    title(
      "Notification preferences",
      "تفضيلات الإشعارات",
      "Choose optional personal reminders and status messages. Security, verification, invitations and clarification messages remain mandatory.",
      "اختر التذكيرات ورسائل الحالة الشخصية الاختيارية. تبقى رسائل الأمان والتحقق والدعوات وطلبات التوضيح إلزامية.",
    ),
    step(
      ".main-content form",
      [
        "Change your preferences",
        "Choose the desired options and save. Optional organization emails must also be enabled for optional messages to be sent.",
      ],
      [
        "تغيير التفضيلات",
        "اختر الإعدادات المطلوبة واحفظ. يجب أيضاً تفعيل البريد الاختياري للمنظمة لإرسال الرسائل الاختيارية.",
      ],
      true,
    ),
  ],
  profile: [
    title(
      "My profile",
      "ملفي الشخصي",
      "Manage your personal details and account security. An administrator controls which personal fields you can edit.",
      "أدر بياناتك الشخصية وأمان حسابك. يحدد المدير الحقول الشخصية التي يمكنك تعديلها.",
    ),
    step(
      ".main-content .tabs",
      [
        "Personal details and security",
        "Use the tabs to switch between personal details and account security. The security tab contains password and authenticator controls when available.",
      ],
      [
        "البيانات الشخصية والأمان",
        "استخدم علامات التبويب للتنقل بين البيانات الشخصية وأمان الحساب. تتضمن علامة الأمان أدوات كلمة المرور والمصادقة عند توفرها.",
      ],
      true,
    ),
    step(
      ".profile-layout .panel.padded",
      [
        "Review your account",
        "Check the identity shown here. Your sign-in email and access roles are administrator-managed.",
      ],
      ["مراجعة الحساب", "تحقق من الهوية المعروضة هنا. يدير المسؤول بريد تسجيل الدخول وأدوار الوصول."],
      true,
    ),
  ],
  assignments: [
    title(
      "Customer assignments",
      "إسناد العملاء",
      "Assign staff to customer organizations. An active customer assignment controls visibility; the assessment team is assigned separately.",
      "أسند أعضاء الفريق إلى منظمات العملاء. يتحكم إسناد العميل النشط في الرؤية، ويُحدد فريق التقييم بشكل منفصل.",
    ),
    actions,
    search,
    rows,
    step(
      ".main-content .panel:nth-of-type(2)",
      [
        "Reassignment queue",
        "Review assessments needing a new team. Open an assessment and assign its team before review proceeds.",
      ],
      [
        "قائمة إعادة الإسناد",
        "راجع التقييمات التي تحتاج فريقاً جديداً. افتح التقييم وحدد فريقه قبل متابعة المراجعة.",
      ],
      true,
    ),
  ],
  staff: [
    title(
      "Staff accounts",
      "حسابات الفريق",
      "Create or manage GRC staff accounts and their roles. Staff use password recovery to set a password and complete required MFA.",
      "أنشئ حسابات فريق GRC وأدرها وأدوارها. يستخدم الفريق استعادة كلمة المرور لتعيينها ويكمل المصادقة المطلوبة.",
    ),
    actions,
    search,
    rows,
  ],
  security: [
    title(
      "Account security",
      "أمان الحساب",
      "Staff MFA is disabled by default. Set a central default and verification method, then override by role or individual staff account. Individual policies take precedence over role policies. Customers always use email OTP. Saving can end affected sessions.",
      "المصادقة الثنائية للفريق معطّلة افتراضياً. حدد السياسة المركزية وطريقة التحقق، ثم تجاوزها حسب الدور أو حساب الموظف الفردي. تتقدم السياسة الفردية على سياسة الدور. يستخدم العملاء دائماً رمز البريد الإلكتروني. قد ينهي الحفظ الجلسات المتأثرة.",
    ),
    search,
    rows,
  ],
  settings: [
    title(
      "GRC settings",
      "إعدادات GRC",
      "Configure policies for results, reports, signup, reminders, scoring, profiles and publication. Changes can affect users immediately.",
      "اضبط سياسات النتائج والتقارير والتسجيل والتذكيرات والاحتساب والملفات والنشر. قد تؤثر التغييرات على المستخدمين فوراً.",
    ),
    step(
      ".main-content form",
      [
        "Review and save policies",
        "Read each section before saving. For example, Before Audit permits a preliminary PDF after submission when downloads are enabled; After Audit waits for report release. Scoring changes apply to future published versions.",
      ],
      [
        "مراجعة السياسات وحفظها",
        "اقرأ كل قسم قبل الحفظ. مثلاً يسمح قبل التدقيق بملف أولي بعد الإرسال عند تفعيل التنزيل؛ أما بعد التدقيق فينتظر إصدار التقرير. تسري تغييرات الاحتساب على الإصدارات المنشورة مستقبلاً.",
      ],
      true,
    ),
    step(
      ".main-content .panel.padded:nth-of-type(2)",
      [
        "Email diagnostics",
        "Check delivery diagnostics and history when verification or notification messages do not arrive.",
      ],
      ["تشخيص البريد", "تحقق من تشخيص الإرسال وسجله عند عدم وصول رسائل التحقق أو الإشعارات."],
      true,
    ),
  ],
  consultations: [
    title(
      "Consultation requests",
      "طلبات الاستشارة",
      "Review incoming requests and track whether they are new, contacted or closed.",
      "راجع الطلبات الواردة وتابع حالتها: جديد أو تم التواصل أو مغلق.",
    ),
    search,
    rows,
  ],
  templates: [
    title(
      "Questionnaire templates",
      "قوالب الاستبيانات",
      "Browse drafts and published versions. A published version is immutable; clone it to make changes.",
      "استعرض المسودات والإصدارات المنشورة. الإصدار المنشور ثابت؛ استنسخه لإجراء التعديلات.",
    ),
    actions,
    search,
    step(
      ".tpl-grid, .main-content .panel",
      [
        "Open or create a template",
        "Open a template to edit or preview it. New assessments use a published version and retain its pinned questionnaire and scoring.",
      ],
      [
        "فتح قالب أو إنشاؤه",
        "افتح قالباً لتعديله أو معاينته. تستخدم التقييمات الجديدة إصداراً منشوراً وتحتفظ بالاستبيان والاحتساب المثبتين.",
      ],
      true,
    ),
  ],
  templateNew: [
    title(
      "Create a template",
      "إنشاء قالب",
      "Enter the required template information and save a draft. Add questions and review scoring before publishing.",
      "أدخل بيانات القالب المطلوبة واحفظ المسودة. أضف الأسئلة وراجع الاحتساب قبل النشر.",
    ),
    step(
      ".main-content form",
      ["Draft details", "Provide the name and framework, then submit the form to create the draft."],
      ["بيانات المسودة", "أدخل الاسم والإطار ثم أرسل النموذج لإنشاء المسودة."],
      true,
    ),
  ],
  templateEdit: [
    title(
      "Template editor",
      "محرر القالب",
      "Edit a draft or inspect a published version. Published versions are read-only; clone to create an editable revision.",
      "عدّل مسودة أو افحص إصداراً منشوراً. الإصدارات المنشورة للقراءة فقط؛ استنسخ لإنشاء نسخة قابلة للتعديل.",
    ),
    step(
      ".tpl-meta-col",
      [
        "Questionnaire and scoring",
        "Set the name, framework, introductions, answer rules, comment and attachment defaults, and scoring points. Supply both language versions.",
      ],
      [
        "الاستبيان والاحتساب",
        "اضبط الاسم والإطار والمقدمات وقواعد الإجابة وافتراضات التعليقات والمرفقات ونقاط الاحتساب. أدخل المحتوى باللغتين.",
      ],
      true,
    ),
    step(
      ".tpl-workspace",
      [
        "Sections and questions",
        "Add and arrange sections and questions, set answers and per-question rules, then save the draft. For example, add Arabic wording for each question before previewing.",
      ],
      [
        "الأقسام والأسئلة",
        "أضف ورتب الأقسام والأسئلة واضبط الإجابات وقواعد السؤال ثم احفظ المسودة. مثلاً أضف النص العربي لكل سؤال قبل المعاينة.",
      ],
      true,
    ),
    actions,
  ],
  templatePreview: [
    title(
      "Customer preview",
      "معاينة العميل",
      "Try the questionnaire and see its live scoring without creating a real assessment. Return to the editor to make changes.",
      "جرّب الاستبيان واحتسابه المباشر دون إنشاء تقييم فعلي. عُد للمحرر لإجراء التعديلات.",
    ),
    step(
      ".iam-stepper",
      [
        "Try sections",
        "Navigate sections and select answers to inspect the customer experience. Preview choices do not submit an assessment.",
      ],
      [
        "تجربة الأقسام",
        "تنقل بين الأقسام واختر الإجابات لمراجعة تجربة العميل. اختيارات المعاينة لا ترسل تقييماً.",
      ],
      true,
    ),
    step(
      ".question-card",
      ["Try an answer", "Select an option and observe how the preliminary score changes."],
      ["تجربة إجابة", "اختر خياراً ولاحظ تغير النتيجة الأولية."],
      true,
    ),
  ],
  siteContent: [
    title(
      "Website content",
      "محتوى الموقع",
      "Manage bilingual public website copy using drafts and role-based approvals. Changes are published only after the final required approval.",
      "أدر نصوص الموقع العامة باللغتين من خلال المسودات والاعتماد حسب الأدوار. لا تُنشر التغييرات إلا بعد الموافقة النهائية المطلوبة.",
    ),
    step(
      ".site-editor .panel:first-of-type",
      [
        "Access and approvals",
        "Administrators choose which existing roles can edit and add approval roles in order. By default, the submitter cannot approve their own submission; an administrator can change that rule.",
      ],
      [
        "الصلاحيات والاعتمادات",
        "يختار المدير الأدوار الحالية المسموح لها بالتعديل ويضيف أدوار الاعتماد بالترتيب. لا يمكن لمقدم الطلب اعتماد طلبه افتراضياً، ويمكن للمدير تغيير هذه القاعدة.",
      ],
      true,
    ),
    step(
      ".visual-editor",
      [
        "Edit both languages",
        "Click text on the visual website to edit English and Arabic together. Add or remove cards and sections with the controls, then save and preview before submission.",
      ],
      [
        "تعديل اللغتين",
        "انقر النص على الموقع المرئي لتعديل الإنجليزية والعربية معاً. أضف البطاقات والأقسام أو أزلها بالأدوات ثم احفظ وعاين قبل الإرسال.",
      ],
      true,
    ),
    step(
      ".site-event",
      ["Audit history", "Expand an event to see its actor, timestamp and recorded changes."],
      ["سجل التدقيق", "وسّع الحدث لعرض المنفذ والوقت والتغييرات المسجلة."],
      true,
    ),
  ],
  guide: [
    title(
      "Help and guides",
      "المساعدة والأدلة",
      "Read the role guide, start the general walkthrough, or download the bilingual PDF. Administrators can select the customer and auditor guides too.",
      "اقرأ دليل الدور أو ابدأ الجولة العامة أو نزّل ملف PDF باللغتين. يمكن للمدير اختيار دليلي العميل والمدقق أيضاً.",
    ),
    step(
      ".guide-intro",
      [
        "Download a guide",
        "Use the PDF link for an offline copy of the selected role guide in both languages.",
      ],
      ["تنزيل دليل", "استخدم رابط PDF للحصول على نسخة دون اتصال لدليل الدور المختار باللغتين."],
      true,
    ),
    step(
      ".guide-sections",
      [
        "Explore the steps",
        "Read each topic and use Open this page to go to the related workspace. Use Take page tour on that page for its specific controls.",
      ],
      [
        "استكشاف الخطوات",
        "اقرأ كل موضوع واستخدم فتح هذه الصفحة للانتقال إلى مكانه. استخدم جولة الصفحة هناك لشرح أدواتها.",
      ],
      true,
    ),
  ],
};
export function pageTourKey(pathname: string): string | undefined {
  if (pathname.replace(/\/$/, "") === "/grc/customer/activity") return "customerDates";
  const path = pathname.replace(/^\/grc\/(customer|auditor)\/?/, "").replace(/\/$/, "");
  if (!path) return "overview";
  if (path === "audit-packages") return "auditPackages";
  if (path === "onboarding-controls") return "onboardingControls";
  if (path === "onboarding") return "onboarding";
  if (/^onboarding\/[^/]+$/.test(path)) return "onboardingDetail";
  if (/^assessments\/[^/]+\/scope$/.test(path)) return "assessmentScope";
  if (/^assessments\/[^/]+$/.test(path)) return "assessment";
  if (/^(organization|customers)\/[^/]+$/.test(path)) return "organization";
  if (/^admin\/templates\/[^/]+\/preview$/.test(path)) return "templatePreview";
  if (path === "admin/templates/new") return "templateNew";
  if (/^admin\/templates\/[^/]+$/.test(path)) return "templateEdit";
  const keys: Record<string, string> = {
    oversight: "oversight",
    assessments: "assessments",
    scorecards: "scorecards",
    organization: "organizations",
    customers: "organizations",
    actions: "actions",
    activity: "activity",
    followups: "followups",
    preferences: "preferences",
    profile: "profile",
    "site-content": "siteContent",
    guide: "guide",
    "admin/assignments": "assignments",
    "admin/staff": "staff",
    "admin/security": "security",
    "admin/settings": "settings",
    "admin/consultations": "consultations",
    "admin/templates": "templates",
  };
  return keys[path];
}
export const getPageTour = (key: string) => pageTours[key] || [];
