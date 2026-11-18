import {test,expect,Page,Locator} from '@playwright/test';

// Route-mocked UI acceptance: no accounts, organizations or shared fixtures are mutated.
const local={name:'100% Saudi with Saudi Commercial Registration',ask_cr:true,add_misa:false};
const foreign={name:'100% foreign working with a Saudi company as a partner',ask_cr:false,add_misa:true};
const branch={name:'Branch of a foreign entity with a Saudi CR and an investment license',ask_cr:true,add_misa:true};
const catalog={industries:[{name:'Financial Services',sectors:['Banking','Other']},{name:'Healthcare and Medical Services',sectors:['Social care','Other']}],nationalities:[local,foreign,branch],general_regulators:['Ministry of Commerce','ZATCA','SDAIA','NCA','HRSD'],industry_regulators:{'Financial Services':['SAMA','CMA'],'Healthcare and Medical Services':['Ministry of Health']},sector_regulators:{'Financial Services|Banking':['SAMA'],'Healthcare and Medical Services|Social care':[]}};
function initial(){return {organization:'QA Organization',industry_type:'Financial Services',industry_sector:'Banking',other_sector:'',company_nationality:local.name,cr_number:'0123456789',ksa_license_type:'Investment license',ksa_license_na:false,ksa_license_rows:[],regulators:[],other_regulator:''};}

async function setup(page:Page,{language='en',canEdit=true,rejectSave=false,rejectExpired=false,display='Dropdown'}={}){
 let profile=initial(),saved:any=null;
 await page.addInitScript(lang=>localStorage.setItem('grc-language',lang),language);
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind:'Customer',user:'profile-ui@example.test',home:'/grc/customer',organizations:[{name:'QA Organization',entity_name:'QA Organization'}],memberships:[{entity:'QA Organization',membership_role:canEdit?'Organization Admin':'Viewer'}],workspace_preferences:{show_page_tour:false,show_help:false}}}}));
 await page.route('**/api/method/ia_maturity.grc.api.organization_detail**',r=>r.fulfill({json:{message:{name:'QA Organization',entity_name:'QA Organization',can_manage:canEdit,can_assign_staff:false,read_only:!canEdit,membership_role:canEdit?'Organization Admin':'Viewer',units:[],members:[],auditors:[],invitations:[]}}}));
 await page.route('**/api/method/ia_maturity.grc.api.profile_catalog**',r=>r.fulfill({json:{message:{...catalog,organization_yes_no_display:display}}}));
 await page.route('**/api/method/ia_maturity.grc.api.organization_profile**',r=>r.fulfill({json:{message:{profile,modified:'v1',can_edit:canEdit,complete:true}}}));
 await page.route('**/api/method/ia_maturity.grc.api.save_organization_profile',r=>{
  saved=r.request().postDataJSON();
  if(rejectSave)return r.fulfill({status:409,json:{exc_type:'TimestampMismatchError',exception:'TimestampMismatchError: Profile changed in another tab.',_server_messages:JSON.stringify([JSON.stringify({message:'Profile changed in another tab.'})])}});
  const candidate=typeof saved.data==='string'?JSON.parse(saved.data):saved.data;
  if(rejectExpired&&candidate.ksa_license_rows.some((row:any)=>row.valid==='Yes'&&row.expiry_date<'2026-11-11'))return r.fulfill({status:417,json:{exception:'ValidationError: A license with a past expiry date cannot be marked valid.'}});
  profile=typeof saved.data==='string'?JSON.parse(saved.data):saved.data;
  return r.fulfill({json:{message:{profile,modified:'v2',can_edit:canEdit,complete:true}}});
 });
 await page.goto('/grc/customer/organization/QA%20Organization');
 await page.getByRole('tab',{name:language==='ar'?'ملف المنشأة':'Company profile',exact:true}).click();
 const form=page.getByTestId('organization-profile');await expect(form).toBeVisible();
 return {form,saved:()=>saved};
}
async function choose(page:Page,form:Locator,label:string,value:string){
 await form.getByRole('combobox',{name:label,exact:true}).click();
 await page.getByRole('option',{name:value,exact:true}).click();
}

test('profile saves leading-zero CR without changing organization identity',async({page})=>{
 const ctx=await setup(page);
 await expect(ctx.form.getByLabel('Saudi CR number (optional)',{exact:true})).toHaveValue('0123456789');
 await ctx.form.getByRole('button',{name:'Save profile',exact:true}).click();
 await expect.poll(()=>ctx.saved()?.entity).toBe('QA Organization');
 const raw=ctx.saved().data,data=typeof raw==='string'?JSON.parse(raw):raw;
 expect(data.cr_number).toBe('0123456789');expect(data.organization).toBe('QA Organization');
 await page.screenshot({path:'test-results/organization-profile-en.png',fullPage:true});
});

test('button presentation saves and clears regulator answers and license validity',async({page})=>{
 const {form,saved}=await setup(page,{display:'Buttons'});
 const regulator=form.getByRole('group',{name:'Ministry of Commerce'});
 await regulator.getByRole('radio',{name:'Not answered',exact:true}).focus();
 await page.keyboard.press('ArrowRight');
 await expect(regulator.getByRole('radio',{name:'Yes',exact:true})).toBeChecked();
 await form.getByRole('button',{name:'Add license',exact:true}).click();
 await form.getByLabel('License name',{exact:true}).fill('QA license');
 const validity=form.getByRole('group',{name:'Still valid?'});
 await validity.getByRole('radio',{name:'No',exact:true}).check();
 await form.getByLabel('Expiry date',{exact:true}).fill('2099-01-01');
 await form.getByRole('button',{name:'Save profile',exact:true}).click();
 await expect.poll(()=>saved()!==null).toBeTruthy();
 let data=typeof saved().data==='string'?JSON.parse(saved().data):saved().data;
 expect(data.regulators.find((r:any)=>r.name==='Ministry of Commerce').answer).toBe('Yes');
 expect(data.ksa_license_rows[0].valid).toBe('No');
 await regulator.getByRole('radio',{name:'Not answered',exact:true}).check();
 await form.getByRole('button',{name:'Save profile',exact:true}).click();
 await expect.poll(()=>{data=typeof saved().data==='string'?JSON.parse(saved().data):saved().data;return data.regulators.find((r:any)=>r.name==='Ministry of Commerce').answer}).toBe('');
});

test('Arabic button presentation honors read-only',async({page})=>{
 const {form}=await setup(page,{display:'Buttons',language:'ar',canEdit:false});
 const regulator=form.getByRole('group',{name:'Ministry of Commerce'});
 await expect(regulator.getByRole('radio',{name:'نعم'})).toBeDisabled();
 await expect(regulator.getByRole('radio',{name:'لم تتم الإجابة'})).toBeChecked();
});

test('nationality clears hidden CR and regulator resolution respects an empty override',async({page})=>{
 const{form}=await setup(page);
 await choose(page,form,'Company nationality',foreign.name);
 await expect(form.getByLabel('Saudi CR number (optional)',{exact:true})).toHaveCount(0);
 await expect(form).toContainText('MISA');
 await choose(page,form,'Company nationality',local.name);
 await expect(form.getByLabel('Saudi CR number (optional)',{exact:true})).toHaveValue('');
 await choose(page,form,'Industry type','Healthcare and Medical Services');
 await choose(page,form,'Industry sector','Social care');
 await expect(form).not.toContainText('Ministry of Health');
 await expect(form).toContainText('Ministry of Commerce');
});

test('Other sector requires its name and N/A hides optional license details',async({page})=>{
 const{form,saved}=await setup(page);
 await choose(page,form,'Industry sector','Other');
 const other=form.getByLabel('Name the sector',{exact:true});await expect(other).toBeVisible();
 await form.getByRole('button',{name:'Save profile',exact:true}).click();
 await expect(form).toContainText('Name the sector.');
 expect(saved()).toBeNull();
 await other.fill('Specialist services');
 await form.getByRole('checkbox',{name:'Not applicable — no KSA license',exact:true}).check();
 await expect(form.getByRole('button',{name:'Add license',exact:true})).toHaveCount(0);
 await form.getByRole('button',{name:'Save profile',exact:true}).click();
 await expect.poll(()=>saved()!==null).toBeTruthy();
});

test('failed save retains the entered profile for recovery',async({page})=>{
 const{form}=await setup(page,{rejectSave:true});
 await form.getByLabel('Other regulator (optional)',{exact:true}).fill('QA regulatory body');
 await form.getByRole('button',{name:'Save profile',exact:true}).click();
 await expect(form).toContainText('Profile changed in another tab');
 await expect(form.getByLabel('Other regulator (optional)',{exact:true})).toHaveValue('QA regulatory body');
});

test('license rows must be complete and server expiry errors remain correctable',async({page})=>{
 await page.clock.install({time:new Date('2026-11-11T12:00:00Z')});
 const{form,saved}=await setup(page,{rejectExpired:true});
 await form.getByRole('button',{name:'Add license',exact:true}).click();
 await form.getByLabel('License name',{exact:true}).fill('QA license');
 await form.getByRole('button',{name:'Save profile',exact:true}).click();
 await expect(form).toContainText('Complete each license row (name, valid, expiry date), or remove it.');
 expect(saved()).toBeNull();
 await choose(page,form,'Still valid?','Yes');
 await form.getByLabel('Expiry date',{exact:true}).fill('2026-11-10');
 await form.getByRole('button',{name:'Save profile',exact:true}).click();
 await expect(form).toContainText('A license with a past expiry date cannot be marked valid.');
 await expect(form.getByLabel('License name',{exact:true})).toHaveValue('QA license');
 await form.getByLabel('Expiry date',{exact:true}).fill('2026-11-11');
 await form.getByRole('button',{name:'Save profile',exact:true}).click();
 await expect(form.getByRole('status')).toContainText('Profile saved.');
});

test('Arabic mobile profile is RTL and read-only users cannot edit',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 const{form}=await setup(page,{language:'ar',canEdit:false});
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 await expect(form.getByLabel('نوع النشاط',{exact:true})).toBeDisabled();
 await expect(form.getByRole('button',{name:/حفظ/})).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 await page.screenshot({path:'test-results/organization-profile-ar-mobile.png',fullPage:true});
});

test('Arabic validation explains missing organization, Other sector and malformed CR',async({page})=>{
 const{form,saved}=await setup(page,{language:'ar'});
 await form.getByLabel('اسم المنشأة',{exact:true}).fill('');
 await form.getByRole('button',{name:'حفظ الملف',exact:true}).click();
 await expect(form).toContainText('أدخل اسم المنشأة.');
 await form.getByLabel('اسم المنشأة',{exact:true}).fill('QA Organization');
 await choose(page,form,'قطاع النشاط','Other');
 await form.getByRole('button',{name:'حفظ الملف',exact:true}).click();
 await expect(form).toContainText('أدخل اسم القطاع.');
 await form.getByLabel('اسم القطاع الآخر',{exact:true}).fill('قطاع متخصص');
 await form.getByLabel('رقم السجل التجاري السعودي (اختياري)',{exact:true}).fill('123');
 await form.getByRole('button',{name:'حفظ الملف',exact:true}).click();
 await expect(form).toContainText('يجب أن يتكون رقم السجل التجاري من 10 أرقام، أو اتركه فارغاً.');
 expect(saved()).toBeNull();
});

for(const language of ['en','ar'])for(const width of [320,390])test(`long nationality stays fully readable: ${language} ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:844});
 const{form}=await setup(page,{language});
 const label=language==='ar'?'جنسية المنشأة':'Company nationality';
 await choose(page,form,label,branch.name);
 const trigger=form.getByRole('combobox',{name:label,exact:true}),selected=trigger.locator('span').first();
 await expect(selected).toHaveText(branch.name);
 await expect(selected).toBeVisible();
 await page.screenshot({path:`test-results/profile-nationality-${language}-${width}.png`,fullPage:true});
 const dimensions=await selected.evaluate(el=>{const style=getComputedStyle(el),range=document.createRange();range.selectNodeContents(el);return {height:el.clientHeight,scrollHeight:el.scrollHeight,width:el.clientWidth,scrollWidth:el.scrollWidth,overflow:style.overflow,lineHeight:style.lineHeight,font:style.font,rangeHeight:range.getBoundingClientRect().height,triggerHeight:el.parentElement?.clientHeight};});
 expect(dimensions.scrollHeight,JSON.stringify(dimensions)).toBeLessThanOrEqual(dimensions.height+1);
 expect(dimensions.scrollWidth,JSON.stringify(dimensions)).toBeLessThanOrEqual(dimensions.width+1);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 await page.screenshot({path:`test-results/profile-nationality-${language}-${width}.png`,fullPage:true});
});

for(const requiresProfile of [true,false])test(`assessment profile gate: ${requiresProfile?'GRC requires save':'IA bypasses profile'}`,async({page})=>{
 const ctx=await setup(page);
 const assessment=()=>({name:'PROFILE-GATE',entity:'QA Organization',template:'QA Template',respondent:'profile-ui@example.test',docstatus:0,profile_required:requiresProfile&&!ctx.saved(),assessment_type:requiresProfile?'GRC':'Internal Audit',question_count:1,answered_count:0,modified:'v1',state:'Draft',current:true,editable:true,review_actions:[],results_visible:false,released:false,sections:[{code:'S1',title:'QA section'}],questions:[{question_code:'Q1',question_text:'Existing assessment question',section_code:'S1',section_title:'QA section',option_a:'A',option_b:'B',option_c:'C',option_d:'D',allow_na:1}]});
 await page.route('**/api/method/ia_maturity.grc.api.assessment?**',r=>r.fulfill({json:{message:assessment()}}));
 await page.route('**/api/method/ia_maturity.grc.api.activity**',r=>r.fulfill({json:{message:[]}}));
 await page.goto('/grc/customer/assessments/PROFILE-GATE');
 if(requiresProfile){
  await expect(page.getByTestId('organization-profile')).toBeVisible();
  await expect(page.locator('.question-card')).toHaveCount(0);
  await page.getByTestId('organization-profile').getByRole('button',{name:'Save profile',exact:true}).click();
 }
 await expect(page.getByTestId('organization-profile')).toHaveCount(0);
 await expect(page.getByText('Existing assessment question',{exact:true})).toBeVisible();
});
