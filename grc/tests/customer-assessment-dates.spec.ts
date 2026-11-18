import {test,expect} from '@playwright/test';
const events=[
 {name:'START',assessment:'DEMO',entity:'Example organization',action:'Assessment started',creation:'2026-11-01T09:00:00Z',actor:'private-actor@example.test',details:'{}'},
 {name:'SAVE',assessment:'DEMO',entity:'Example organization',action:'Answers changed',creation:'2026-11-01T10:00:00Z',actor:'private-actor@example.test',details:'{"questions":["Q1"]}'},
 {name:'FINISH',assessment:'DEMO',entity:'Example organization',action:'Submitted',creation:'2026-11-02T09:00:00Z',actor:'private-actor@example.test',details:'{}'},
 {name:'FILE',assessment:'DEMO',entity:'Example organization',action:'Evidence uploaded',creation:'2026-11-02T10:00:00Z',actor:'private-actor@example.test',details:'{"filename":"private-evidence.pdf"}'}
];
for(const kind of ['Customer','Auditor']) test(kind+' assessment history presentation',async({page})=>{
 const base=kind==='Customer'?'/grc/customer':'/grc/auditor';
 await page.addInitScript(()=>localStorage.setItem('grc-language','en'));
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind,user:'date-demo',full_name:'Demonstration user',home:base,organizations:[{name:'ORG',entity_name:'Example organization'}],memberships:[{entity:'ORG',membership_role:'Organization Admin'}],workspace_preferences:{show_help:false,show_page_tour:false}}}}));
 await page.route('**/api/method/ia_maturity.grc.api.activity**',r=>r.fulfill({json:{message:events}}));
 await page.route('**/api/method/ia_maturity.grc.api.dashboard**',r=>r.fulfill({json:{message:{counts:{},assessments:[],total:0,overdue:0,overdue_actions_count:0,overdue_actions:[],recent_activity:events}}}));
 await page.route('**/api/method/ia_maturity.grc.api.assessment?**',r=>r.fulfill({json:{message:{name:'DEMO',grc_assignment:'ASSIGN',entity:'Example organization',modified:'v1',editable:false,docstatus:1,review_actions:[],questions:[],results_visible:false}}}));
 for(const path of ['/activity','/assessments/DEMO','']){
  await page.goto(base+path);
  if(path==='/assessments/DEMO')await page.getByText(kind==='Customer'?'Assessment dates':'Assessment activity',{exact:true}).last().click();
  if(kind==='Customer'){
   await expect(page.locator('.main-content')).toContainText('Assessment started');await expect(page.locator('.main-content')).toContainText('Assessment finished');
   await expect(page.locator('.main-content')).not.toContainText('Answers changed');await expect(page.locator('.main-content')).not.toContainText('Evidence uploaded');await expect(page.locator('.main-content')).not.toContainText('private-actor');await expect(page.locator('.main-content')).not.toContainText('private-evidence');
  }else await expect(page.locator('.main-content')).toContainText('Answers changed');
 }
});
