import {test,expect,Page} from '@playwright/test';
test.beforeEach(async({page})=>{await page.addInitScript(()=>sessionStorage.setItem('grc-assessment-view:qa%40example.test:QA','normal'))});
import {readFileSync} from 'node:fs';
const questions=[{question_code:'Q1',section_code:'S1',section_title:'Completed domain',question_text:'First question',selected_option:'C',option_a:'A',option_b:'B',option_c:'C',option_d:'D'},{question_code:'Q2',section_code:'S2',section_title:'Pending domain',question_text:'Second question',selected_option:'',option_a:'A',option_b:'B',option_c:'C',option_d:'D'}];
async function fixture(page:Page,mode:string,kind='Customer',complete=false){
 const doc:any={name:'QA',entity:'Example',template:'Default',docstatus:0,editable:true,results_visible:false,review_actions:[],released:false,overall_maturity_visibility:mode,questions:questions.map((q,i)=>({...q,allow_na:1,selected_option:complete||i===0?'C':''})),scoring:{points:{A:25,B:50,C:75,D:100},max_points:100,bands:[{level_name:'High',min_score:0}],sections:[{code:'S1'},{code:'S2'}]},expand_maturity:true};
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind,user:'qa@example.test',home:kind==='Customer'?'/grc/customer':'/grc/auditor',organizations:[],workspace_preferences:{show_page_tour:false,show_help:false}}}}));
 await page.route('**/api/method/ia_maturity.grc.api.assessment?**',r=>r.fulfill({json:{message:doc}}));
 await page.route('**/api/method/ia_maturity.grc.api.activity**',r=>r.fulfill({json:{message:[]}}));
 await page.route('**/api/method/ia_maturity.grc.api.save_assessment',r=>{const answers=r.request().postDataJSON().answers;doc.questions=doc.questions.map((q:any)=>({...q,selected_option:answers[q.question_code]?.selected_option||''}));return r.fulfill({json:{message:doc}})});
 await page.goto((kind==='Customer'?'/grc/customer':'/grc/auditor')+'/assessments/QA');return doc;
}
for(const kind of ['Customer','Auditor'])test('hidden removes the whole maturity panel for '+kind,async({page})=>{
 await fixture(page,'Hidden',kind,true);await expect(page.locator('.maturity-disclosure')).toHaveCount(0);await expect(page.locator('.iam-live-score')).toHaveCount(0);
});
test('after completion appears only after final answer',async({page})=>{
 await fixture(page,'After assessment completion');await expect(page.locator('.maturity-disclosure')).toHaveCount(0);
 await page.locator('.iam-stepper button').nth(1).click();await page.locator('input[type=radio][value=D]').check();
 await expect(page.locator('.maturity-disclosure')).toBeVisible();await expect(page.locator('.score-value')).toContainText('87.5');await expect(page.locator('.score-row')).toHaveCount(2);
});
test('completed sections only excludes pending domains and every overall score',async({page})=>{
 await fixture(page,'Completed sections only');await expect(page.locator('.maturity-disclosure')).toBeVisible();await expect(page.locator('.maturity-disclosure .score-row')).toHaveCount(1);await expect(page.locator('.maturity-disclosure')).toContainText('Completed domain');await expect(page.locator('.maturity-disclosure')).not.toContainText('Pending domain');await expect(page.locator('.score-value')).toHaveCount(0);await expect(page.locator('.iam-live-score')).toHaveCount(0);
});
test('manager can save panel display mode in portal',async({page})=>{
 let mode='Hidden';await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind:'Auditor',staff_roles:['GRC Manager'],user:'qa@example.test',home:'/grc/auditor',organizations:[],workspace_preferences:{show_page_tour:false,show_help:false}}}}));
 await page.route('**/api/method/ia_maturity.grc.api.maturity_display_settings',r=>r.fulfill({json:{message:{mode,options:['Hidden','After assessment completion','Completed sections only']}}}));
 await page.route('**/api/method/ia_maturity.grc.api.save_maturity_display',r=>{mode=r.request().postDataJSON().mode;return r.fulfill({json:{message:{mode}}})});
 await page.goto('/grc/auditor/assessment-display');await page.getByRole('combobox',{name:'Overall Maturity panel'}).click();await page.getByRole('option',{name:'Completed sections only',exact:true}).click();await page.getByRole('button',{name:'Save display setting'}).click();await expect.poll(()=>mode).toBe('Completed sections only');await page.reload();await expect(page.getByRole('combobox')).toContainText('Completed sections only');
});

test('not applicable completes a section without fabricating a score',async({page})=>{
 await fixture(page,'Completed sections only');await page.locator('.iam-stepper button').nth(1).click();await page.locator('input[value="N/A"]').check();await expect(page.locator('.maturity-disclosure .score-row')).toHaveCount(2);await expect(page.locator('.maturity-disclosure .score-row').last()).toContainText('Not applicable');await expect(page.locator('.maturity-disclosure .score-row').last().locator('.progress-track')).toHaveCount(0);
});
for(const role of ['GRC Manager','GRC App Admin'])test('native staff Desk display control saves for '+role,async({page})=>{
 await page.goto('about:blank');await page.setContent('<div id="wrapper"><div class="layout-main-section"></div></div>');
 await page.addScriptTag({content:readFileSync(new URL('../../../frappe/frappe/public/js/lib/jquery/jquery.min.js',import.meta.url),'utf8')});
 await page.evaluate(role=>{
  const w=window as any;w.__=(s:string)=>s;w.saved=null;
  w.frappe={pages:{'grc-staff':{}},session:{user:'desk@example.test'},user_roles:[role],msgprint:()=>{},show_alert:(v:any)=>w.notice=v,ui:{make_app_page:()=>({set_primary_action:()=>{}}),form:{make_control:({parent,df}:any)=>{const el=document.createElement('select');el.setAttribute('aria-label',df.label);df.options.split('\n').forEach((v:string)=>{const op=document.createElement('option');op.value=op.text=v;el.add(op)});parent.append(el);return{set_value:(v:string)=>el.value=v,get_value:()=>el.value}}}},xcall:async(method:string,args:any)=>{if(method.endsWith('maturity_display_settings'))return{mode:'Hidden',options:['Hidden','After assessment completion','Completed sections only']};if(method.endsWith('save_maturity_display')){w.saved=args;return{mode:args.mode}}return[]}};
 },role);
 await page.addScriptTag({content:readFileSync(new URL('../../ia_maturity/ia_maturity/page/grc_staff/grc_staff.js',import.meta.url),'utf8')});
 await page.evaluate(()=>{const w=window as any;w.frappe.pages['grc-staff'].on_page_load(document.getElementById('wrapper'))});
 await page.getByRole('combobox',{name:'Overall Maturity panel'}).selectOption('Completed sections only');await page.getByRole('button',{name:'Save display setting'}).click();
 await expect.poll(()=>page.evaluate(()=>(window as any).saved?.mode)).toBe('Completed sections only');expect(await page.evaluate(()=>(window as any).saved.expected_mode)).toBe('Hidden');
});

test('all N/A answers complete assessment without a misleading zero score',async({page})=>{
 const doc=await fixture(page,'After assessment completion','Customer',true);doc.questions.forEach((q:any)=>q.selected_option='N/A');await page.reload();await expect(page.locator('.maturity-disclosure .score-value')).toHaveText('Not applicable');await expect(page.locator('.maturity-disclosure h2')).toHaveCount(0);
});
