import {test,expect} from '@playwright/test';
import {activeAssessmentTemplates} from '../src/assessmentTemplates';
const templates=[{name:'OFF',template_name:'Inactive default',version:1,is_active:0,grc_published:1,is_default:true},{name:'DRAFT',template_name:'Unpublished draft',version:2,is_active:1,grc_published:0},{name:'ACTIVE',template_name:'Active questionnaire',version:3,is_active:1,grc_published:1},{name:'ACTIVE2',template_name:'Another active questionnaire',version:4,is_active:'1',grc_published:'1'}];
test('unit: only explicitly active published templates are selectable without changing management data',()=>{
 expect(activeAssessmentTemplates(templates).map(t=>t.name)).toEqual(['ACTIVE','ACTIVE2']);expect(templates).toHaveLength(4);
 expect(activeAssessmentTemplates([{name:'missing'},{name:'inactive',is_active:0,grc_published:1},{name:'draft',is_active:1,grc_published:0}])).toEqual([]);expect(activeAssessmentTemplates()).toEqual([]);
});
for(const kind of ['Customer','Auditor'])for(const empty of [false,true])test(kind+' creation filters inactive templates; empty='+empty,async({page})=>{
 await page.addInitScript(()=>localStorage.setItem('grc-language','en'));
 const home=kind==='Customer'?'/grc/customer':'/grc/auditor';
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind,is_admin:kind==='Auditor',user:'qa@example.test',home,organizations:[{name:'ORG',entity_name:'Test organization'}],memberships:[{entity:'ORG',membership_role:'Organization Admin'}],workspace_preferences:{show_page_tour:false,show_help:false}}}}));
 await page.route('**/api/method/ia_maturity.grc.api.dashboard**',r=>r.fulfill({json:{message:{counts:{},assessments:[],total:0,customer_count:1,overdue:0,recent_activity:[],overdue_actions:[],overdue_actions_count:0}}}));
 await page.route('**/api/method/ia_maturity.grc.api.templates',r=>r.fulfill({json:{message:empty?templates.slice(0,2):templates}}));
 await page.goto(home);await page.getByRole('button',{name:'Start assessment',exact:true}).click();
 const modal=page.getByRole('dialog'),selector=modal.getByRole('combobox',{name:'Template',exact:true});
 if(empty){await expect(selector).toBeDisabled();await expect(modal.getByRole('button',{name:'Start assessment',exact:true})).toBeDisabled();await expect(modal).toContainText('No active published assessment templates are available.');return}
 await expect(selector).toContainText('Active questionnaire');await selector.click();await expect(page.getByRole('option')).toHaveCount(2);await expect(page.getByRole('option',{name:'Inactive default'})).toHaveCount(0);await expect(page.getByRole('option',{name:'Unpublished draft'})).toHaveCount(0);await page.getByRole('option',{name:'Another active questionnaire · v4',exact:true}).click();await expect(modal.locator('select[name=template]')).toHaveValue('ACTIVE2');
});
