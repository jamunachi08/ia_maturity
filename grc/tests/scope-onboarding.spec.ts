import {test,expect,type Page} from '@playwright/test';
const user='packages-demo@example.test';
const sections=[{code:'a',title:'Governance',title_ar:'الحوكمة',question_count:2},{code:'b',title:'Risk management',title_ar:'إدارة المخاطر',question_count:2},{code:'c',title:'Compliance',title_ar:'الامتثال',question_count:1}];
const config={required_sections:['a'],packages:[{code:'risk',label:'Risk assurance',label_ar:'تأكيد المخاطر',description:'Assess risk planning and response.',description_ar:'تقييم تخطيط المخاطر والاستجابة لها.',sections:['b']},{code:'combined',label:'Risk and compliance',label_ar:'المخاطر والامتثال',description:'Combine risk and compliance coverage.',description_ar:'اجمع تغطية المخاطر والامتثال.',sections:['b','c']}]};
async function mock(page:Page,role='manager',lang='en'){
 await page.addInitScript(({user,lang})=>{localStorage.setItem('grc-language',lang);localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(user)+':skip-auto','1')},{user,lang});
 const customer=role==='customer';
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind:customer?'Customer':'Auditor',user,full_name:'Demonstration user',home:customer?'/grc/customer':'/grc/auditor',organizations:[],staff_roles:role==='manager'?['GRC Manager']:['GRC Auditor'],is_admin:role==='admin',can_invite_customers:!customer,can_configure_scope:['admin','manager'].includes(role),can_operations:role==='manager'||role==='admin'}}}));
 page.on('pageerror',error=>{throw error});
}
async function packages(page:Page){
 await page.route('**/api/method/ia_maturity.grc.api.scope_configurations**',r=>r.fulfill({json:{message:{templates:[{name:'DEMO',template_name:'Demonstration questionnaire',version:1,is_active:1,assessment_type:'GRC',grc_is_default:1,modified:'v1'}],sections,configurations:[{name:'CFG1',version:1,published:1,configuration:config,modified:'v1'}]}}}));
}
test('manager previews combined packages, publishes a new version and replays safe tour',async({page})=>{
 await mock(page);await packages(page);let sent:any,published=0;
 await page.route('**/api/method/ia_maturity.grc.api.save_scope_configuration',r=>{sent=r.request().postDataJSON();return r.fulfill({json:{message:{name:'CFG2',modified:'v2'}}})});
 await page.route('**/api/method/ia_maturity.grc.api.publish_scope_configuration',r=>{published++;return r.fulfill({json:{message:{name:'CFG2'}}})});
 await page.goto('/grc/auditor/audit-packages');await page.getByRole('combobox',{name:'Questionnaire version'}).click();await page.getByRole('option',{name:/Demonstration/}).click();
 const preview=page.locator('[data-tour=package-preview]');await expect(preview).toContainText('Questions: 2');await preview.getByRole('checkbox',{name:/Risk assurance/}).check();await preview.getByRole('checkbox',{name:/Risk and compliance/}).check();await expect(preview).toContainText('Questions: 5');
 await page.getByRole('button',{name:'Take page tour'}).click();await expect(page.getByRole('dialog',{name:'Audit packages'})).toBeVisible();await page.keyboard.press('Escape');expect(published).toBe(0);
 await page.getByLabel('Package label',{exact:true}).first().fill('Risk assurance package');await page.getByRole('button',{name:'Save and publish'}).click();await expect(page.getByRole('status').filter({hasText:'Saved'})).toBeVisible();expect(sent.configuration.packages[0].label).toBe('Risk assurance package');expect(sent.name).toBeUndefined();expect(published).toBe(1);
 await page.screenshot({path:'test-results/packages-manager.png',fullPage:true});await preview.screenshot({path:'test-results/packages-preview.png'});
 await page.goto('/grc/auditor/guide');await expect(page.getByRole('heading',{name:'GRC manager guide'})).toBeVisible();await expect(page.getByRole('link',{name:'Download bilingual PDF'})).toHaveAttribute('href','/assets/ia_maturity/guides/manager-guide.pdf');await page.getByRole('combobox',{name:'Choose a guide'}).click();await expect(page.getByRole('option',{name:'Administrator guide'})).toHaveCount(0);await page.getByRole('option',{name:'Auditor guide'}).click();await expect(page.getByRole('heading',{name:'Auditor guide'})).toBeVisible();
});
test('customer confirms scope before answering and sees only included questions in live score',async({page})=>{
 await mock(page,'customer');let chosen:any;
 const doc:any={name:'QA',entity:'Demonstration company',template:'DEMO',modified:'v1',docstatus:0,editable:false,scope_editable:true,question_count:0,answered_count:0,current:true,review_actions:[],results_visible:true,overall_maturity_visibility:'After assessment completion',scope:{...config,configuration:'CFG1',version:1,sections,selected_packages:[],selected_sections:[],confirmed:false,acknowledgement_required:false,can_correct:false},questions:[],scoring:{points:{A:25,B:50,C:75,D:100},max_points:100,bands:[{level_name:'High',min_score:0,color:'#12506e'}]},customer_score_timing:'During assessment'};
 await page.route('**/api/method/ia_maturity.grc.api.assessment?**',r=>r.fulfill({json:{message:doc}}));
 await page.route('**/api/method/ia_maturity.grc.api.confirm_assessment_scope',r=>{chosen=r.request().postDataJSON();doc.scope={...doc.scope,confirmed:true,selected_sections:['a'],sections:sections.map(s=>({...s,included:s.code==='a'}))};doc.editable=true;doc.question_count=2;doc.questions=[1,2].map(i=>({question_code:'Q'+i,section_code:'a',section_title:'Governance',question_text:'Governance practice '+i,option_a:'Ad hoc',option_b:'Basic',option_c:'Established',option_d:'Leading',allow_comment:0,allow_attachment:0}));return r.fulfill({json:{message:doc}})});
 await page.route('**/api/method/ia_maturity.grc.api.save_assessment',r=>{for(const [k,v] of Object.entries(r.request().postDataJSON().answers))Object.assign(doc.questions.find((q:any)=>q.question_code===k),v);return r.fulfill({json:{message:doc}})});
 await page.route('**/api/method/ia_maturity.grc.api.activity**',r=>r.fulfill({json:{message:[]}}));
 await page.goto('/grc/customer/assessments/QA');await expect(page).toHaveURL(/\/scope$/);await expect(page.locator('.question-card')).toHaveCount(0);await page.locator('[data-tour=scope-confirmation]').screenshot({path:'test-results/customer-scope.png'});await page.getByRole('button',{name:'Confirm scope and continue'}).click();await expect(page.locator('.question-card')).toHaveCount(2);expect(chosen.packages).toEqual([]);await expect(page.locator('[data-tour=scope-summary]')).toContainText('Risk management — Not assessed');await page.locator('input[value=D]').first().check();await page.locator('input[value=B]').last().check();await expect(page.locator('.iam-live-pct')).toContainText('75');
});
const invitation={name:'INV-DEMO',email:'customer@example.test',invited_by:user,status:'Started',delivery_status:'Sent by mail system',creation:'2026-11-01 10:00:00',last_sent_on:'2026-11-01 10:01:00',expires_on:'2026-11-08 10:01:00',last_activity_on:'2026-11-01 10:10:00',started_on:'2026-11-01 10:10:00',blocker:'Email verification incomplete',next_action:'Customer verifies email',needs_attention:true,permitted_actions:['remind','resend','revoke'],events:[{action:'Invitation queued',at:'2026-11-01 10:01:00',actor:user}]};
test('auditor sends a recipient-specific request and monitors manual follow-up without draft values',async({page})=>{
 await mock(page,'auditor');let created:any,action:any;
 await page.route('**/api/method/ia_maturity.grc.api.onboarding_invitations**',r=>r.fulfill({json:{message:[invitation]}}));
 await page.route('**/api/method/ia_maturity.grc.api.onboarding_detail**',r=>r.fulfill({json:{message:invitation}}));
 await page.route('**/api/method/ia_maturity.grc.api.create_onboarding_invitation',r=>{created=r.request().postDataJSON();return r.fulfill({json:{message:invitation}})});
 await page.route('**/api/method/ia_maturity.grc.api.onboarding_invitation_action',r=>{action=r.request().postDataJSON();return r.fulfill({json:{message:invitation}})});
 await page.goto('/grc/auditor/onboarding');await page.getByRole('button',{name:'Invite customer',exact:true}).click();const dialog=page.getByRole('dialog');await dialog.getByLabel('Customer email').fill('new@example.test');await dialog.getByRole('button',{name:'Send invitation'}).click();await expect(dialog).toHaveCount(0);expect(created).toEqual({email:'new@example.test',language:'en'});
 await page.getByRole('link',{name:'Open',exact:true}).click();await expect(page.getByText('Original inviting auditor')).toBeVisible();await expect(page.getByText(/It does not prove delivery/)).toBeVisible();await expect(page.getByLabel('Organization name')).toHaveCount(0);await page.getByRole('button',{name:'Take page tour'}).click();await page.keyboard.press('Escape');expect(action).toBeUndefined();await page.getByRole('button',{name:'Send reminder'}).click();await expect.poll(()=>action?.action).toBe('remind');await page.screenshot({path:'test-results/onboarding-auditor.png',fullPage:true});await page.locator('[data-tour=onboarding-progress]').screenshot({path:'test-results/onboarding-progress.png'});
});
test('Arabic package preview and customer scope stay usable on mobile',async({page})=>{
 await page.setViewportSize({width:390,height:844});await mock(page,'manager','ar');await packages(page);await page.goto('/grc/auditor/audit-packages');await page.getByRole('combobox').click();await page.getByRole('option',{name:/Demonstration/}).click();await expect(page.locator('html')).toHaveAttribute('dir','rtl');const preview=page.locator('[data-tour=package-preview]');await preview.getByRole('checkbox',{name:/تأكيد المخاطر/}).check();await expect(preview).toContainText('الأسئلة: 4');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:'test-results/packages-mobile-ar.png',fullPage:true});await page.getByRole('button',{name:'جولة الصفحة'}).click();await expect(page.getByRole('dialog',{name:'حزم التدقيق'})).toBeVisible();await page.keyboard.press('Escape');
});
test('admin controls require a reason and preserve defaults while tours remain passive',async({page})=>{
 await mock(page,'admin');let changes:any;
 await page.route('**/api/method/ia_maturity.grc.api.ownership_settings**',r=>r.fulfill({json:{message:{auto_lock:true,attention_hours:48}}}));
 await page.route('**/api/method/ia_maturity.grc.api.save_ownership_settings',r=>{changes=r.request().postDataJSON();return r.fulfill({json:{message:{auto_lock:true,attention_hours:72}}})});
 await page.goto('/grc/auditor/onboarding-controls');await page.getByRole('button',{name:'Take page tour'}).click();await page.keyboard.press('Escape');expect(changes).toBeUndefined();await page.getByLabel('Needs attention after hours').fill('72');await page.getByRole('button',{name:'Save controls'}).click();expect(changes).toBeUndefined();await page.getByLabel('Reason').fill('Allow three working days');await page.getByRole('button',{name:'Save controls'}).click();await expect.poll(()=>changes?.attention_hours).toBe('72');expect(changes.auto_lock).toBe(1);
});

for (const role of ['manager','admin']) test(role+' manages template availability and default',async({page})=>{
 await mock(page,role);await packages(page);let changed:any;
 await page.route('**/api/method/ia_maturity.grc.api.set_template_type',r=>{changed=r.request().postDataJSON();return r.fulfill({json:{message:{name:'DEMO'}}})});
 await page.goto('/grc/auditor/audit-packages');
 await page.getByRole('combobox',{name:'Questionnaire version'}).click();
 await page.getByRole('option',{name:/Demonstration.*Default/}).click();
 await page.getByRole('checkbox',{name:'Active template',exact:true}).uncheck();
 await expect(page.getByRole('checkbox',{name:'Make default for this assessment type'})).toBeDisabled();
 await page.getByRole('button',{name:'Save template settings'}).click();
 await expect.poll(()=>changed?.is_active).toBe(0);
 expect(changed.make_default).toBe(0);
 await page.getByRole('checkbox',{name:'Active template',exact:true}).check();
 await page.getByRole('checkbox',{name:'Make default for this assessment type'}).check();
 await page.getByRole('button',{name:'Save template settings'}).click();
 await expect.poll(()=>changed?.make_default).toBe(1);
 expect(changed.assessment_type).toBe('GRC');
 await page.locator('section').filter({has:page.getByRole('heading',{name:'Template availability and default'})}).screenshot({path:'test-results/template-controls-'+role+'.png'});
});

for(const role of ['manager','admin'])test(role+' can clear every mandatory section and publish individual choices',async({page})=>{
 await mock(page,role);let sent:any;
 await page.route('**/api/method/ia_maturity.grc.api.scope_configurations**',r=>r.fulfill({json:{message:{templates:[{name:'DEMO',template_name:'Demonstration questionnaire',version:1,is_active:1,assessment_type:'GRC',modified:'v1'}],sections,configurations:[]}}}));
 await page.route('**/api/method/ia_maturity.grc.api.save_scope_configuration',r=>{sent=r.request().postDataJSON();return r.fulfill({json:{message:{name:'CFG2',modified:'v2'}}})});
 await page.route('**/api/method/ia_maturity.grc.api.publish_scope_configuration',r=>r.fulfill({json:{message:{name:'CFG2'}}}));
 await page.goto('/grc/auditor/audit-packages');await page.getByRole('combobox',{name:'Questionnaire version'}).click();await page.getByRole('option',{name:/Demonstration/}).click();
 const mandatory=page.locator('[data-tour=required-sections]');await expect(mandatory.getByRole('checkbox')).toHaveCount(3);for(const box of await mandatory.getByRole('checkbox').all())await box.uncheck();
 const preview=page.locator('[data-tour=package-preview]');await expect(preview.getByRole('checkbox')).toHaveCount(3);await expect(preview.locator('.scope-total')).toHaveText('Included sections: 0 · Questions: 0');
 await preview.getByRole('checkbox',{name:/Risk management/}).check();await expect(preview.locator('.scope-total')).toHaveText('Included sections: 1 · Questions: 2');
 await page.getByRole('button',{name:'Save and publish'}).click();await expect(page.getByRole('status').filter({hasText:'Saved'})).toBeVisible();expect(sent.configuration.required_sections).toEqual([]);expect(sent.configuration.packages.map((p:any)=>p.sections)).toEqual([['a'],['b'],['c']]);
 await preview.screenshot({path:'test-results/all-optional-'+role+'.png'});
});

test('mandatory sections are locked in packages and preview with a deduplicated question breakdown',async({page})=>{
 await mock(page);await packages(page);await page.goto('/grc/auditor/audit-packages');await page.getByRole('combobox',{name:'Questionnaire version'}).click();await page.getByRole('option',{name:/Demonstration/}).click();
 const editor=page.locator('[data-tour=package-editor]');for(const box of await editor.getByRole('checkbox',{name:/Governance/}).all()){await expect(box).toBeChecked();await expect(box).toBeDisabled()}
 const preview=page.locator('[data-tour=package-preview]');const required=preview.getByRole('checkbox',{name:/Governance/});await expect(required).toBeChecked();await expect(required).toBeDisabled();await expect(preview.locator('.mandatory-section')).toContainText('Mandatory section');
 await preview.getByRole('checkbox',{name:/Risk assurance/}).check();await preview.getByRole('checkbox',{name:/Risk and compliance/}).check();await expect(preview.locator('.scope-breakdown li')).toHaveCount(3);await expect(preview.locator('.scope-total')).toHaveText('Included sections: 3 · Questions: 5');
 await page.locator('[data-tour=required-sections]').getByRole('checkbox',{name:/Governance/}).uncheck();await expect(preview.getByRole('checkbox',{name:/Governance/})).toBeEnabled();await expect(preview.locator('.scope-total')).toHaveText('Included sections: 2 · Questions: 3');
});
