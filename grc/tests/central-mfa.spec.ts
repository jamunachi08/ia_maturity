import {test,expect,Page} from '@playwright/test';

const user='central-admin@example.test';
async function mockApp(page:Page,{guest=false,policy='Enforced',method='OTP App',kind='Auditor',admin=true}:{guest?:boolean;policy?:string|null;method?:string;kind?:string;admin?:boolean}={}){
 let signedIn=!guest;
 await page.addInitScript(user=>{
  localStorage.setItem('grc-language','en');
  localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(user)+':skip-auto','1');
 },user);
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',route=>route.fulfill({json:{message:signedIn?
  {enabled:true,kind,user,full_name:'Central Administrator',is_admin:kind==='Auditor'&&admin,home:kind==='Auditor'?'/grc/auditor':'/grc/customer',organizations:[]}:
  {enabled:true,kind:'Guest',home:'/login'}}}));
 await page.route('**/api/method/ia_maturity.grc.api.security_mfa_settings**',route=>route.fulfill({json:{message:{policy,method,email_ready:true,blanket_mfa:true,centralized:true}}}));
 await page.route('**/api/method/ia_maturity.grc.api.security_accounts**',route=>route.fulfill({json:{message:{rows:[{name:user,full_name:'Central Administrator',kind:'Auditor',policy:'Default',roles:['GRC App Admin'],required:policy==='Enforced',email_verified:true,enrolled:true},{name:'customer@example.test',full_name:'OTP Customer',kind:'Customer',policy:'Email OTP',roles:['GRC Customer'],required:false,email_verified:true,enrolled:false}],has_more:false}}}));
 await page.route('**/api/method/ia_maturity.grc.api.security_role_policies**',route=>route.fulfill({json:{message:[{role:'GRC Consultant',policy:'Default'},{role:'GRC Reviewer',policy:'Required'}]}}));
 return ()=>{signedIn=false};
}

test('admin selects the central policy and email method, then signs in again',async({page})=>{
 const signOut=await mockApp(page);
 let sent:any;
 await page.route('**/api/method/ia_maturity.grc.api.save_mfa_settings',route=>{
  sent=route.request().postDataJSON();signOut();
  return route.fulfill({json:{message:{policy:sent.policy,method:sent.method,affected:8,reauthenticate:true}}});
 });
 await page.goto('/grc/auditor/admin/security');
 await expect(page.getByRole('heading',{name:'Central MFA settings'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Edit security',exact:true})).toHaveCount(1);
 await expect(page.getByRole('button',{name:'Edit role policy',exact:true})).toHaveCount(2);
 const policy=page.getByRole('combobox',{name:'MFA policy',exact:true});
 await policy.click();
 for(const label of ['Enabled','Disabled','Enforced'])await expect(page.getByRole('option',{name:label,exact:true})).toBeVisible();
 await page.getByRole('option',{name:'Enabled',exact:true}).click();
 await policy.click();await page.getByRole('option',{name:'Enforced',exact:true}).click();
 await page.getByRole('combobox',{name:'Verification method',exact:true}).click();
 await expect(page.getByRole('option',{name:'Authenticator app',exact:true})).toBeVisible();
 await page.getByRole('option',{name:'Email code',exact:true}).click();
 await page.getByLabel('Your current password').fill('local-test-password');
 await page.screenshot({path:'test-results/central-mfa-desktop.png',fullPage:true,animations:'disabled'});
 await page.getByRole('button',{name:'Save central MFA settings'}).click();
 await expect(page).toHaveURL(/\/login$/);
 expect(sent).toMatchObject({policy:'Enforced',method:'Email',current_password:'local-test-password'});
});

test('central controls translate to Arabic and fit a mobile viewport',async({page})=>{
 await mockApp(page,{policy:'Disabled',method:'Email'});
 await page.goto('/grc/auditor/admin/security');
 await page.getByRole('button',{name:'العربية',exact:true}).click();
 await page.setViewportSize({width:390,height:844});
 await expect(page.getByRole('heading',{name:'إعدادات المصادقة المركزية'})).toBeVisible();
 await expect(page.getByRole('combobox',{name:'طريقة التحقق',exact:true})).toBeVisible();
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 await expect.poll(async()=>(await page.locator('.sidebar').boundingBox())!.x).toBeGreaterThanOrEqual(390);
 await expect.poll(()=>page.locator('.account-security-status .table-scroll').evaluate(el=>el.scrollWidth>el.clientWidth)).toBe(true);
 const size=await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth}));
 expect(size.width).toBeLessThanOrEqual(size.viewport);
 await page.screenshot({path:'test-results/central-mfa-arabic-mobile.png',fullPage:true,animations:'disabled'});
 await page.getByRole('button',{name:'تعديل سياسة الدور',exact:true}).first().click();
 const dialog=page.getByRole('dialog',{name:'سياسة المصادقة للدور'});
 await expect(dialog.getByRole('combobox',{name:'سياسة المصادقة الثنائية'})).toBeVisible();
 const bounds=await dialog.boundingBox();
 expect(bounds!.x).toBeGreaterThanOrEqual(0);expect(bounds!.x+bounds!.width).toBeLessThanOrEqual(390);
 await page.screenshot({path:'test-results/central-mfa-arabic-mobile-editor.png',animations:'disabled'});
 await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
});

for(const policy of ['Enabled','Disabled','Enforced']){
 test('profile email MFA reflects '+policy,async({page})=>{
  const signOut=await mockApp(page,{policy,method:'Email',kind:'Auditor'});
  let sent:any;
  await page.route('**/api/method/ia_maturity.grc.api.profile**',route=>route.fulfill({json:{message:{
   name_repair_fields:[],email:user,full_name:'Central Administrator',kind:'Auditor',modified:'1',
   values:{},fields:[],editable_fields:[],time_zones:[],authenticator:{policy,method:'Email',centralized:true,
    available:true,enrolled:false,required:policy==='Enforced',can_enroll:policy==='Enabled',optional_enrolled:false}
  }}}));
  await page.route('**/api/method/ia_maturity.grc.api.set_optional_mfa',route=>{
   sent=route.request().postDataJSON();signOut();return route.fulfill({json:{message:{enabled:true,redirect:'/login'}}});
  });
  await page.goto('/grc/auditor/profile');
  await page.getByRole('tab',{name:'Account security',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Email verification codes'})).toBeVisible();
  const button=page.getByRole('button',{name:'Enable email codes',exact:true});
  if(policy==='Enabled'){
   await expect(button).toBeVisible();
   await page.getByLabel('Current password',{exact:true}).first().fill('local-test-password');
   await button.click();await expect(page).toHaveURL(/\/login$/);
   expect(sent).toMatchObject({enabled:1,current_password:'local-test-password'});
  }else{
   await expect(button).toHaveCount(0);
   await expect(page.getByText(policy==='Disabled'?'MFA is disabled by your GRC administrator.':'Sign in with your password, then enter the code sent to your registered email.')).toBeVisible();
  }
 });
}

test('password sign-in presents the native email verification field',async({page})=>{
 await mockApp(page,{guest:true});
 let sent:any;
 await page.route('**/api/method/login',route=>{
  sent=route.request().postDataJSON();
  return route.fulfill({json:{tmp_id:'Ab123456',verification:{method:'Email',setup:true,token_delivery:true,prompt:'Verification code has been sent to your registered email address.'}}});
 });
 await page.goto('/login?staff=1');await page.getByLabel('Email or username').fill(user);
 await page.getByLabel('Password',{exact:true}).fill('local-test-password');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page.getByLabel('Verification code',{exact:true})).toBeVisible();
 await expect(page.getByLabel('Authenticator code',{exact:true})).toHaveCount(0);
 await page.getByLabel('Verification code',{exact:true}).fill('012345');
 await page.getByRole('button',{name:'Verify and continue'}).click();
 await expect.poll(()=>sent?.otp).toBe('012345');
 expect(sent.tmp_id).toBe('Ab123456');
});

test('staff MFA defaults to Disabled and customers have no policy editor',async({page})=>{
 await mockApp(page,{policy:null});
 await page.goto('/grc/auditor/admin/security');
 await expect(page.getByRole('combobox',{name:'MFA policy',exact:true})).toHaveText('Disabled');
 await expect(page.getByText('Staff MFA is disabled by default.',{exact:false})).toBeVisible();
 const customer=page.getByRole('row').filter({hasText:'customer@example.test'});
 await expect(customer.getByRole('button')).toHaveCount(0);
 await expect(customer.getByText('Email OTP',{exact:true})).toHaveCount(2);
});

test('admin requires MFA for a role while the central default is Disabled',async({page})=>{
 await mockApp(page,{policy:'Disabled'});
 let sent:any;
 await page.route('**/api/method/ia_maturity.grc.api.set_role_mfa_policy',route=>{
  sent=route.request().postDataJSON();return route.fulfill({json:{message:{affected:2}}});
 });
 await page.goto('/grc/auditor/admin/security');
 await page.getByRole('row').filter({hasText:'GRC Consultant'}).getByRole('button',{name:'Edit role policy'}).click();
 const dialog=page.getByRole('dialog',{name:'MFA role policy'});
 await dialog.getByRole('combobox',{name:'MFA policy'}).click();
 await page.getByRole('option',{name:'Required',exact:true}).click();
 await dialog.getByLabel('Your current password').fill('local-test-password');
 await dialog.getByRole('button',{name:'Save policy',exact:true}).click();
 await expect(dialog).toHaveCount(0);
 expect(sent).toEqual({role:'GRC Consultant',policy:'Required',current_password:'local-test-password'});
});

test('admin disables MFA for a username and retains the editor on rejection',async({page})=>{
 await mockApp(page);
 let sent:any,accepted=false;
 await page.route('**/api/method/ia_maturity.grc.api.set_mfa_policy',route=>{
  sent=route.request().postDataJSON();
  return accepted?route.fulfill({json:{message:{sessions_revoked:true}}}):route.fulfill({status:403,json:{message:'Current password is incorrect.'}});
 });
 await page.goto('/grc/auditor/admin/security');
 await page.getByRole('row').filter({hasText:user}).getByRole('button',{name:'Edit security'}).click();
 const dialog=page.getByRole('dialog',{name:'Individual MFA policy'});
 await dialog.getByRole('combobox',{name:'MFA policy'}).click();
 await page.getByRole('option',{name:'Disabled',exact:true}).click();
 await dialog.getByLabel('Your current password').fill('wrong-test-password');
 await dialog.getByRole('button',{name:'Save policy',exact:true}).click();
 await expect(dialog.getByRole('alert')).toContainText('Current password is incorrect.');
 expect(sent).toEqual({user,policy:'Disabled',current_password:'wrong-test-password'});
 accepted=true;
 await dialog.getByLabel('Your current password').fill('local-test-password');
 await dialog.getByRole('button',{name:'Save policy',exact:true}).click();
 await expect(dialog).toHaveCount(0);
 expect(sent.current_password).toBe('local-test-password');
});

test('customer profile keeps email OTP with no password or optional MFA controls',async({page})=>{
 await mockApp(page,{policy:'Disabled',kind:'Customer'});
 await page.route('**/api/method/ia_maturity.grc.api.profile**',route=>route.fulfill({json:{message:{
  name_repair_fields:[],email:user,full_name:'OTP Customer',kind:'Customer',modified:'1',values:{},fields:[],editable_fields:[],time_zones:[],authenticator:{policy:'Disabled',required:false}
 }}}));
 await page.goto('/grc/customer/profile');
 await page.getByRole('tab',{name:'Account security',exact:true}).click();
 await expect(page.getByText('Customers sign in with an email code every time. No password is needed.')).toBeVisible();
 await expect(page.locator('input[type="password"]')).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Enable email codes',exact:true})).toHaveCount(0);
});

test('staff without admin access cannot open security configuration',async({page})=>{
 await mockApp(page,{admin:false});
 await page.route('**/api/method/ia_maturity.grc.api.dashboard**',route=>route.fulfill({json:{message:{stats:[],assessments:[],reports:[],recent_activity:[]}}}));
 await page.goto('/grc/auditor/admin/security');
 await expect(page).toHaveURL(/\/grc\/auditor$/);
 await expect(page.getByRole('heading',{name:'Central MFA settings'})).toHaveCount(0);
 await expect(page.getByRole('link',{name:'Account security',exact:true})).toHaveCount(0);
});
