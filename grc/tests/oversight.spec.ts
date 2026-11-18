import {test,expect} from '@playwright/test';
const manager='manager@example.test';
const policy={onboarding:true,assignments:true,stages:['GRC Manager','GRC App Admin'],allow_self:false};
async function mock(page:any,lang='en'){
 await page.addInitScript(({user,lang}:any)=>{localStorage.setItem('grc-language',lang);localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(user)+':skip-auto','1')},{user:manager,lang});
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',(r:any)=>r.fulfill({json:{message:{enabled:true,kind:'Auditor',user:manager,full_name:'Portfolio Manager',home:'/grc/auditor',can_operations:true,is_admin:false,organizations:[{name:'ACME',entity_name:'Acme Company'}]}}}));
 const data={is_admin:false,policy,customer_policies:{ACME:policy},customers:[{name:'ACME',entity_name:'Acme Company',sector:'Other',contact_email:'customer@example.test',is_active:1}],auditors:[{name:manager,full_name:'Portfolio Manager',enabled:1,roles:['GRC Manager']},{name:'auditor@example.test',full_name:'Audit Reviewer',enabled:1,roles:['GRC Reviewer']}],assignments:[{name:'ASN',entity:'ACME',auditor:manager,responsibility:'Manager'}],requests:[{name:'REQ-1',kind:'Customer Assignment',entity:'ACME',status:'Pending',requested_by:'auditor@example.test',step:0,creation:'2026-11-01 12:00:00',payload:{entity:'ACME',auditor:'auditor@example.test',responsibility:'Reviewer',active:1},workflow:policy,decisions:[]}]};
 await page.route('**/api/method/ia_maturity.grc.api.operations_overview**',(r:any)=>r.fulfill({json:{message:data}}));
 await page.route('**/api/method/ia_maturity.grc.api.operations_detail**',(r:any)=>r.fulfill({json:{message:{profile:{name:'ACME',entity_name:'Acme Company',sector:'Other',contact_email:'customer@example.test',members:[{name:'M',user:'customer@example.test',membership_role:'Organization Admin',active:1}],units:[{name:'U',unit_name:'Audit',unit_type:'Department',responsibilities:'Internal audit'}]},assessments:[{name:'ASSIGN-1',assessment:'ASSESS-1',entity:'ACME',respondent:'customer@example.test',reviewer:'auditor@example.test',workflow_state:'Submitted'}],actions:[],followups:[],activity:[{name:'ACT-1',action:'Organization updated',actor:manager,entity:'ACME',creation:'2026-11-01',details:'{"notes":"Updated"}'}],activity_summary:{'Organization updated':1}}}}));
 return data;
}
test('manager explores customer reports, exports activity and reviews an allocation',async({page})=>{
 page.on('pageerror',error=>{throw error});const data=await mock(page);let decision:any;
 await page.route('**/api/method/ia_maturity.grc.api.operations_decide**',r=>{decision=r.request().postDataJSON();data.requests[0].status='Approved';return r.fulfill({json:{message:{status:'Approved'}}})});
 await page.goto('/grc/auditor/oversight');await expect(page.getByRole('heading',{name:'Customer and auditor overview'})).toBeVisible();await expect(page.getByRole('button',{name:'Global workflow'})).toHaveCount(0);
 await page.getByRole('button',{name:'View overview'}).click();const modal=page.getByRole('dialog');await expect(modal.getByRole('heading',{name:'Acme Company'})).toBeVisible();await expect(modal.getByText('Internal audit')).toBeVisible();
 await modal.getByRole('button',{name:'Assessments (1)'}).click();await expect(modal.getByRole('link',{name:'ASSESS-1'})).toHaveAttribute('href','/grc/auditor/assessments/ASSESS-1');
 await modal.getByRole('button',{name:'Activity (1)'}).click();await modal.getByText('View details').click();await expect(modal.getByText('{"notes":"Updated"}')).toBeVisible();const downloadPromise=page.waitForEvent('download');await modal.getByRole('button',{name:'Export CSV'}).click();expect((await downloadPromise).suggestedFilename()).toBe('customer-activity.csv');await modal.getByRole('button',{name:'Close',exact:true}).click();
 await page.getByRole('tab',{name:'Approvals',exact:true}).click();await page.getByRole('button',{name:'Review request'}).click();await page.getByLabel('Decision reason').fill('Customer allocation verified');await page.getByRole('button',{name:'Submit decision'}).click();expect(decision).toEqual({name:'REQ-1',decision:'Approve',comment:'Customer allocation verified'});await expect(page.getByRole('cell',{name:'Approved',exact:true})).toBeVisible();
 await page.screenshot({path:'test-results/oversight-manager.png',fullPage:true});
});
test('Arabic mobile workflow uses shared dropdowns and preserves ordered approval stages',async({page})=>{
 await page.setViewportSize({width:390,height:844});await mock(page,'ar');let sent:any;
 await page.route('**/api/method/ia_maturity.grc.api.operations_configure**',r=>{sent=r.request().postDataJSON();return r.fulfill({json:{message:{ok:true}}})});
 await page.goto('/grc/auditor/oversight');await page.getByRole('button',{name:'مسار الاعتماد',exact:true}).click();const dialog=page.getByRole('dialog',{name:'مسار اعتماد العمليات'});await dialog.getByRole('combobox',{name:'اشتراط اعتماد التسجيل'}).click();await page.getByRole('option',{name:'لا',exact:true}).click();await expect(dialog.getByRole('combobox',{name:'اشتراط اعتماد التسجيل'})).toContainText('لا');await page.screenshot({path:'test-results/oversight-mobile-ar.png',fullPage:false});await dialog.getByRole('button',{name:'حفظ التغييرات'}).click();expect(sent.entity).toBe('ACME');expect(sent.config.onboarding).toBe(false);expect(sent.config.stages).toEqual(['GRC Manager','GRC App Admin']);
});


test('new overview tour supports first visit, skip, replay and Arabic',async({page})=>{
 await mock(page);
 await page.addInitScript(user=>localStorage.removeItem('grc-page-tour:v1:'+encodeURIComponent(user)+':skip-auto'),manager);
 await page.goto('/grc/auditor/oversight');await expect(page.getByRole('dialog',{name:'Customer and auditor overview'})).toBeVisible();await page.getByRole('button',{name:'Skip tour',exact:true}).click();await page.getByRole('button',{name:'Take page tour'}).click();await expect(page.getByRole('dialog',{name:'Customer and auditor overview'})).toBeVisible();await page.keyboard.press('Escape');await page.getByRole('button',{name:'العربية',exact:true}).click();await page.getByRole('button',{name:'جولة الصفحة'}).click();await expect(page.getByRole('dialog',{name:'نظرة عامة على العملاء والمدققين'})).toBeVisible();
});
