import {test,expect,type Page} from '@playwright/test';

type Options={kind?:'Customer'|'Auditor';type?:'Internal Audit'|'GRC';state?:string;editable?:boolean;actions?:string[];current?:boolean;language?:string;focus?:boolean;profile?:boolean;scope?:boolean};
const points={A:25,B:50,C:75,D:100};
async function fixture(page:Page,options:Options={}){
 const kind=options.kind||'Customer',type=options.type||'Internal Audit',user=kind==='Customer'?'ux-customer@example.test':'ux-reviewer@example.test';
 const editable=options.editable??kind==='Customer',name='UX-A';
 const doc:any={name,entity:'Demo company',respondent:'ux-customer@example.test',report_recipient:'ux-customer@example.test',template:'UX template',modified:'v1',docstatus:editable?0:1,state:options.state||(editable?'Draft':'Submitted'),assessment_type:type,current:options.current??true,editable,review_actions:options.actions||[],released:options.state==='Report Released',results_visible:false,grc_assignment:'UX-ASSIGNMENT',expand_report:true,allow_report_download:1,allow_report_email:1,report_access_timing:'After Audit',questions:[{question_code:'Q1',section_code:'S1',section_title:'First section',question_text:'Is the policy documented?',option_a:'No policy',option_b:'Developing policy',option_c:'Documented policy',option_d:'Improved policy',allow_na:1},{question_code:'Q2',section_code:'S2',section_title:'Second section',question_text:'Is it reviewed?',option_a:'Never',option_b:'Sometimes',option_c:'Regularly',option_d:'Continuously',allow_na:1}],scoring:{points,max_points:100,bands:[]},question_count:2,answered_count:0};
 if(options.profile)doc.profile_required=true;
 if(options.scope){doc.scope_editable=true;doc.scope={configuration:'GRC scope',version:1,required_sections:['Awareness'],minimum_optional_sections:1,minimum_packages:['risk'],invited_sections:['Awareness','Risk'],packages:[{code:'risk',label:'Risk',label_ar:'المخاطر',description:'',sections:['Risk']},{code:'governance',label:'Governance',label_ar:'الحوكمة',description:'',sections:['Governance']}],sections:[{code:'Awareness',title:'GRC General Maturity Awareness',question_count:2},{code:'Risk',title:'Risk',question_count:17},{code:'Governance',title:'Governance',question_count:14}],selected_packages:['risk'],selected_sections:['Awareness','Risk'],confirmed:false,acknowledgement_required:false,can_correct:false};}
 const session={enabled:true,kind,user,allowed_assessment_types:[type],audit_type_access:{[doc.entity]:[type]},home:kind==='Customer'?'/grc/customer':'/grc/auditor',organizations:[{name:doc.entity,entity_name:doc.entity}],memberships:[{entity:doc.entity,membership_role:'Organization Admin'}],assignments:[{entity:doc.entity,responsibility:'Reviewer'}],department_memberships:[{department:type,role:'Reviewer'}],staff_roles:['GRC Reviewer'],workspace_preferences:{show_page_tour:false,show_help:false}};
 await page.addInitScript(({user,language,focus,name})=>{localStorage.setItem('grc-language',language);if(!focus)sessionStorage.setItem('grc-assessment-view:'+encodeURIComponent(user)+':'+name,'normal')},{user,language:options.language||'en',focus:!!options.focus,name});
 const calls:{method:string;args:any}[]=[];
 let failSave=false;
 await page.route('**/api/method/**',async route=>{
  const method=new URL(route.request().url()).pathname.split('.').pop()||'';
  const args=route.request().method()==='POST'?route.request().postDataJSON():{};
  if(method==='bootstrap')return route.fulfill({json:{message:session}});
  if(method==='assessment')return route.fulfill({json:{message:doc}});
  if(method==='activity')return route.fulfill({json:{message:[]}});
  if(method==='dashboard')return route.fulfill({json:{message:{counts:{},assessments:[],total:0,overdue:0,customer_count:1,overdue_actions_count:0,overdue_actions:[],recent_activity:[]}}});
  if(method==='profile_catalog')return route.fulfill({json:{message:{industries:[{name:'Financial Services',sectors:['Banking']}],nationalities:[{name:'Saudi',ask_cr:true,add_misa:false}],general_regulators:[],industry_regulators:{},sector_regulators:{}}}});
  if(method==='organization_profile')return route.fulfill({json:{message:{profile:{organization:'Demo company',industry_type:'',industry_sector:'',company_nationality:'',ksa_license_na:false,ksa_license_type:'',ksa_license_rows:[],regulators:[]},modified:'profile-1',can_edit:true,complete:false}}});
  if(method==='organization_detail')return route.fulfill({json:{message:{auditors:[],members:[]}}});
  if(method==='save_assessment'){
   calls.push({method,args});
   if(failSave)return route.fulfill({status:409,json:{message:'A newer assessment version is available.'}});
   for(const q of doc.questions)q.selected_option=args.answers[q.question_code]?.selected_option||'';
   doc.modified='v'+(calls.length+1);
   return route.fulfill({json:{message:doc}});
  }
  if(method==='transition'){
   calls.push({method,args});
   if(args.action==='start_review'){doc.state='Under Review';doc.review_actions=['clarify','approve'];}
   if(args.action==='approve'){doc.state='Approved';doc.review_actions=['release'];}
   if(args.action==='release'){doc.state='Report Released';doc.released=true;doc.review_actions=[];}
   if(args.action==='clarify'){doc.state='Clarification Required';doc.clarification=args.comment;doc.review_actions=[];}
   return route.fulfill({json:{message:doc}});
  }
  if(method==='submit_assessment'){calls.push({method,args});doc.docstatus=1;doc.editable=false;doc.state='Submitted';return route.fulfill({json:{message:doc}});}
  if(method==='email_report'){calls.push({method,args});return route.fulfill({json:{message:{queued:true}}});}
  return route.fulfill({json:{message:[]}});
 });
 return {doc,calls,failSave:(value:boolean)=>{failSave=value},home:session.home};
}

for(const type of ['Internal Audit','GRC'] as const){
 test(type+' section overview links to missing questions and updates after an answer',async({page})=>{
  await fixture(page,{type,focus:true});await page.goto('/grc/customer/assessments/UX-A');
  const overview=page.locator('#assessment-section-overview');
  await expect(overview.getByRole('button',{name:'Go to unanswered question Q1'})).toBeVisible();
  await expect(overview.getByRole('button',{name:'Go to unanswered question Q2'})).toBeVisible();
  await overview.getByRole('button',{name:'Go to unanswered question Q2'}).click();
  await expect(page.locator('#question-Q2')).toHaveClass(/is-unanswered/);
  await expect(page.locator('#question-Q2 input').first()).toBeFocused();
  await page.locator('#question-Q2 input[value="N/A"]').check();
  await expect(page.locator('#question-Q2')).not.toHaveClass(/is-unanswered/);
  await expect(overview.getByRole('button',{name:'Go to unanswered question Q2'})).toHaveCount(0);
  await expect(overview.getByRole('button',{name:'Go to unanswered question Q1'})).toBeVisible();
 });
 test(type+' incomplete answers have an actionable next step and a safe save-and-exit',async({page})=>{
  const f=await fixture(page,{type});
  await page.goto('/grc/customer/assessments/UX-A');
  await expect(page.getByRole('region',{name:'Your next step'})).toContainText('Changes save automatically');
  await page.getByRole('button',{name:'Next section',exact:true}).click();
  await expect(page.getByRole('button',{name:'Submit for review',exact:true})).toBeDisabled();
  await expect(page.getByText('Answer every shown question before submitting. N/A counts as an answer where it is available.')).toBeVisible();
  await page.getByRole('button',{name:'Go to first unanswered question',exact:true}).last().click();
  await expect(page.getByRole('heading',{name:'Is the policy documented?',exact:true})).toBeVisible();
  await page.locator('input[value="C"]').check();
  await page.getByRole('button',{name:'Save and exit',exact:true}).click();
  await expect(page).toHaveURL('/grc/customer/assessments');
  expect(f.calls.some(c=>c.method==='save_assessment'&&c.args.answers.Q1.selected_option==='C')).toBe(true);
 });
 test(type+' assigned reviewer gets the correct begin, approval and release next steps',async({page})=>{
  const f=await fixture(page,{type,kind:'Auditor',editable:false,actions:['start_review']});
  await page.goto('/grc/auditor/assessments/UX-A');
  const next=page.getByRole('region',{name:'Your next step'});
  await expect(next).toContainText('Choose Begin review');
  await page.getByRole('button',{name:'Begin review',exact:true}).click();
  await page.getByRole('dialog').getByRole('button',{name:'Cancel',exact:true}).click();
  expect(f.calls.filter(c=>c.method==='transition')).toHaveLength(0);
  for(const action of ['Begin review','Approve assessment','Release report']){
   await page.getByRole('button',{name:action,exact:true}).click();
   await page.getByRole('dialog').getByRole('button',{name:'Confirm',exact:true}).click();
   if(action==='Begin review')await expect(next).toContainText('Request clarification');
   if(action==='Approve assessment')await expect(next).toContainText('Release report publishes');
  }
  await expect(next).toContainText('official report has been released');
  expect(f.calls.filter(c=>c.method==='transition').map(c=>c.args.action)).toEqual(['start_review','approve','release']);
 });
 test(type+' complete answers explain submission and the locked review state',async({page})=>{
  const f=await fixture(page,{type});await page.goto('/grc/customer/assessments/UX-A');
  await page.locator('input[value="C"]').check();await page.getByRole('button',{name:'Next section',exact:true}).click();
  await page.locator('input[value="N/A"]').check();
  await expect(page.getByRole('region',{name:'Your next step'})).toContainText('All shown questions are answered');
  await expect(page.getByRole('button',{name:'Submit for review',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Submit for review',exact:true}).click();
  await expect(page.getByRole('region',{name:'Your next step'})).toContainText('No action is needed unless');
  await expect(page.getByRole('button',{name:'Submit for review',exact:true})).toHaveCount(0);
  expect(f.calls.filter(c=>c.method==='submit_assessment')).toHaveLength(1);
 });
}

test('hidden overview retains Arabic missing-question navigation',async({page})=>{
 const f=await fixture(page,{type:'GRC',language:'ar',focus:true});f.doc.customer_sections_visibility='Hidden';
 await page.goto('/grc/customer/assessments/UX-A');
 await expect(page.locator('#assessment-section-overview')).toHaveCount(0);
 await page.getByRole('button',{name:'انتقل إلى السؤال غير المجاب Q2'}).click();
 await expect(page.locator('#question-Q2')).toBeVisible();
 await expect(page.locator('#question-Q2 input').first()).toBeFocused();
});

test('clarification requires an explanation and then tells staff to wait for customer resubmission',async({page})=>{
 const f=await fixture(page,{kind:'Auditor',editable:false,state:'Under Review',actions:['clarify','approve']});
 await page.goto('/grc/auditor/assessments/UX-A');await page.getByRole('button',{name:'Request clarification',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Request clarification'});await dialog.getByRole('button',{name:'Confirm',exact:true}).click();
 expect(f.calls.filter(c=>c.method==='transition')).toHaveLength(0);
 await dialog.getByLabel('Review comment',{exact:true}).fill('Please explain how the policy is reviewed.');
 await dialog.getByRole('button',{name:'Confirm',exact:true}).click();
 await expect(page.getByRole('region',{name:'Your next step'})).toContainText('Waiting for the customer to respond');
 expect(f.calls.find(c=>c.method==='transition')?.args.comment).toBe('Please explain how the policy is reviewed.');
});

test('failed autosave explains unsaved work, prevents exit, and supports a successful retry',async({page})=>{
 const f=await fixture(page);f.failSave(true);
 await page.goto('/grc/customer/assessments/UX-A');
 await page.locator('input[value="C"]').check();
 await page.getByRole('button',{name:'Save and exit',exact:true}).click();
 await expect(page).toHaveURL('/grc/customer/assessments/UX-A');
 await expect(page.locator('.save-state')).toHaveText('Save failed');
 await expect(page.getByText('Your latest changes have not been saved. Retry saving before leaving this page.')).toBeVisible();
 await expect(page.locator('input[value="C"]')).toBeChecked();
 f.failSave(false);await page.getByRole('button',{name:'Retry save',exact:true}).click();
 await expect(page.locator('.save-state')).toHaveText('Saved');
 await page.getByRole('button',{name:'Save and exit',exact:true}).click();
 await expect(page).toHaveURL('/grc/customer/assessments');
});

test('customer focus mode keeps next-step guidance and save-and-exit visible',async({page})=>{
 await fixture(page,{focus:true});await page.goto('/grc/customer/assessments/UX-A');
 await expect(page.locator('.assessment-questionnaire-content').getByText(/Answer every shown question\. Use N\/A where offered/)).toBeVisible();
 await expect(page.getByRole('button',{name:'Save and exit',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Normal view',exact:true}).click();
 await expect(page.getByRole('region',{name:'Your next step'})).toBeVisible();
});

test('a failed submission does not mislabel already saved answers as unsaved',async({page})=>{
 const f=await fixture(page);for(const question of f.doc.questions)question.selected_option='C';
 await page.route('**/api/method/ia_maturity.grc.api.submit_assessment',route=>route.fulfill({status:409,json:{message:'The assessment could not be submitted. Please retry.'}}));
 await page.goto('/grc/customer/assessments/UX-A');await page.getByRole('button',{name:'Next section',exact:true}).click();
 await page.getByRole('button',{name:'Submit for review',exact:true}).click();
 await expect(page.getByRole('alert')).toContainText('The assessment could not be submitted.');
 await expect(page.locator('.save-state')).toHaveText('Saved');await expect(page.locator('.save-state')).not.toHaveClass(/error/);
 await expect(page.getByText('Your latest changes have not been saved. Retry saving before leaving this page.')).toHaveCount(0);
});

test('submitted customer, unassigned staff and historical revision each explain why editing is unavailable',async({page})=>{
 const f=await fixture(page,{editable:false,state:'Submitted'});
 await page.goto('/grc/customer/assessments/UX-A');
 await expect(page.getByRole('region',{name:'Your next step'})).toContainText('No action is needed unless');
 await expect(page.getByRole('button',{name:'Submit for review',exact:true})).toHaveCount(0);
 await expect(page.locator('input[value="C"]').first()).toBeDisabled();
 f.doc.current=false;await page.reload();
 await expect(page.getByRole('region',{name:'Your next step'})).toContainText('earlier assessment revision');
});

test('staff without review actions gets assignment guidance without invented approval rights',async({page})=>{
 await fixture(page,{kind:'Auditor',editable:false,actions:[]});await page.goto('/grc/auditor/assessments/UX-A');
 await expect(page.getByRole('region',{name:'Your next step'})).toContainText('assigned authorized reviewer');
 await expect(page.getByRole('button',{name:'Approve assessment',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Release report',exact:true})).toHaveCount(0);
});

test('GRC required profile explains the gate and allows returning without starting answers',async({page})=>{
 const f=await fixture(page,{type:'GRC',profile:true});await page.goto('/grc/customer/assessments/UX-A');
 await expect(page.getByTestId('organization-profile')).toContainText('assessment stays blocked until the profile is valid');
 await expect(page.locator('.question-card')).toHaveCount(0);
 await page.getByRole('button',{name:'Save profile',exact:true}).click();
 await expect(page.getByRole('alert')).toContainText('Select the industry type.');
 await page.getByRole('link',{name:'Back to assessments',exact:true}).click();
 await expect(page).toHaveURL(f.home+'/assessments');
});

test('GRC mandatory scope retains invitation minima while offering a safe exit',async({page})=>{
 await fixture(page,{type:'GRC',scope:true});await page.goto('/grc/customer/assessments/UX-A');
 await expect(page).toHaveURL('/grc/customer/assessments/UX-A/scope');
 await expect(page.getByText('You can return to assessments now. Questions remain unavailable until the required scope is confirmed. Leaving this screen does not save unconfirmed choices.')).toBeVisible();
 await expect(page.getByRole('checkbox').first()).toBeDisabled();
 await expect(page.getByRole('checkbox').nth(1)).toBeChecked();
 await expect(page.getByRole('checkbox').nth(1)).toBeDisabled();
 await expect(page.locator('.question-card')).toHaveCount(0);
 await page.getByRole('link',{name:'Back to assessments',exact:true}).click();
 await expect(page).toHaveURL('/grc/customer/assessments');
});

test('report actions explain administrator restrictions and email can be cancelled without sending',async({page})=>{
 const f=await fixture(page,{editable:false});
 Object.assign(f.doc,{allow_report_download:0,can_email_report:true,report_access_timing:'Before Audit',report_preliminary:true});
 await page.goto('/grc/customer/assessments/UX-A');
 await expect(page.getByRole('button',{name:'Download PDF',exact:true})).toBeDisabled();
 await expect(page.getByText('Disabled by the platform administrator.',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Email report',exact:true}).click();
 await expect(page.getByRole('dialog').getByLabel('Recipient')).toHaveAttribute('readonly','');
 await page.getByRole('dialog').getByRole('button',{name:'Cancel',exact:true}).click();
 expect(f.calls.filter(c=>c.method==='email_report')).toHaveLength(0);
});

test('team selection explains an empty eligible roster and permits cancellation',async({page})=>{
 const f=await fixture(page,{kind:'Auditor',editable:false});f.doc.can_assign=true;f.doc.reviewer='assigned-reviewer@example.test';
 await page.goto('/grc/auditor/assessments/UX-A');await page.getByRole('button',{name:'Assign team',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Assign team'});
 await expect(dialog).toContainText('ask a department manager to update the customer assignments first');
 await expect(dialog.getByRole('combobox',{name:'Reviewer',exact:true})).toContainText('assigned-reviewer@example.test');
 await dialog.getByRole('button',{name:'Cancel',exact:true}).click();await expect(dialog).toHaveCount(0);
});

test('Arabic mobile assessment next steps and save exit stay readable with keyboard access',async({page})=>{
 await page.setViewportSize({width:390,height:844});await fixture(page,{type:'GRC',language:'ar'});await page.goto('/grc/customer/assessments/UX-A');
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 await expect(page.getByRole('region',{name:'خطوتك التالية',exact:true})).toBeVisible();
 const exit=page.getByRole('button',{name:'الحفظ والخروج',exact:true});await expect(exit).toBeVisible();
 await exit.focus();await expect(exit).toBeFocused();
 const sizes=await page.evaluate(()=>({width:document.documentElement.scrollWidth,viewport:innerWidth}));expect(sizes.width).toBeLessThanOrEqual(sizes.viewport);
 await page.screenshot({path:'test-results/ux-assessment-arabic-mobile.png',fullPage:true,animations:'disabled'});
});
