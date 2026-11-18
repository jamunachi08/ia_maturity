import {test,expect,Page} from '@playwright/test';
async function admin(page:Page){
 await page.addInitScript(()=>localStorage.setItem('grc-language','en'));
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind:'Auditor',is_admin:true,user:'admin@example.test',home:'/grc/auditor',organizations:[],workspace_preferences:{show_page_tour:false,show_help:false}}}}));
}
test('admin saves customer visibility settings',async({page})=>{
 await admin(page);let saved:any;
 const settings={scoring:{points_a:25,points_b:50,points_c:75,points_d:100},profile_fields:[],profile_editable_fields:[],delivery:[],default_due_days:14,reminder_days:7};
 await page.route('**/api/method/ia_maturity.grc.api.settings',r=>r.fulfill({json:{message:settings}}));
 await page.route('**/api/method/ia_maturity.grc.api.email_delivery**',r=>r.fulfill({json:{message:[]}}));
 await page.route('**/api/method/ia_maturity.grc.api.save_settings',r=>{saved=r.request().postDataJSON().data;return r.fulfill({json:{message:settings}})});
 await page.goto('/grc/auditor/admin/settings');
 await page.getByRole('combobox',{name:'Customer scoring visibility',exact:true}).click();await page.getByRole('option',{name:'During assessment',exact:true}).click();
 await page.getByRole('combobox',{name:'Customer section overview',exact:true}).click();await page.getByRole('option',{name:'Hidden',exact:true}).click();
 await page.getByRole('button',{name:'Save changes',exact:true}).first().click();
 await expect.poll(()=>saved?.customer_score_timing).toBe('During assessment');expect(saved.customer_sections_visibility).toBe('Hidden');expect(Number(saved.question_extras_enabled)).toBe(0);
});
test('default template editing creates an editable revision with default-off extras',async({page})=>{
 await admin(page);let cloned=false,published:any;
 const base:any={name:'DEFAULT',template_name:'Default questionnaire',version:1,grc_published:1,is_default:true,framework:'IIA Global Internal Audit Standards',modified:'v1',weighting_method:'Points (each question equal)',sections:[{section_code:'S1',section_title:'Governance',weight:1}],questions:[{question_code:'Q1',section_code:'S1',question_text:'Governance question',option_a:'A',option_b:'B',option_c:'C',option_d:'D'}]};
 const draft={...base,name:'REVISION',template_name:'Default revision',version:2,modified:'v2',grc_published:0,is_default:false,grc_default_revision:1};
 await page.route('**/api/method/ia_maturity.grc.api.templates?**',r=>{const name=new URL(r.request().url()).searchParams.get('name');return r.fulfill({json:{message:name==='REVISION'?draft:base}})});
 await page.route('**/api/method/ia_maturity.grc.api.settings',r=>r.fulfill({json:{message:{scoring:{}}}}));
 await page.route('**/api/method/ia_maturity.grc.api.save_template',r=>{cloned=r.request().postDataJSON().clone===1;return r.fulfill({json:{message:{name:'REVISION'}}})});
 await page.route('**/api/method/ia_maturity.grc.api.publish_template',r=>{published=r.request().postDataJSON();draft.grc_published=1;return r.fulfill({json:{message:{name:'REVISION'}}})});
 await page.goto('/grc/auditor/admin/templates/DEFAULT');await page.getByRole('button',{name:'Edit default template',exact:true}).click();await expect(page).toHaveURL(/templates\/REVISION$/);expect(cloned).toBe(true);
 await expect(page.getByRole('textbox',{name:'Template name',exact:true})).toBeEditable();
 await expect(page.getByRole('combobox',{name:'Allow comments by default',exact:true})).toContainText('Disabled');
 await expect(page.getByRole('combobox',{name:'Allow attachments by default',exact:true})).toContainText('Disabled');
 await expect(page.getByRole('checkbox',{name:'Use as default for new assessments'})).toBeChecked();
 await page.getByRole('button',{name:'Publish version',exact:true}).click();await expect.poll(()=>published?.make_default).toBe(1);
});
