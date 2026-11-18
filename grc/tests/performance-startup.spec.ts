import {test,expect} from '@playwright/test';

const guest={enabled:true,kind:'Guest',home:'/login'};
const auditor={enabled:true,kind:'Auditor',home:'/grc/auditor',user:'perf-staff@example.test',full_name:'Performance Staff',organizations:[],staff_roles:['GRC Auditor'],workspace_preferences:{show_page_tour:false,show_help:false}};
const dashboard={assessments:[],total:0,page:1,page_size:15,counts:{},overdue:0,customer_count:0,needs_reassignment:0,overdue_actions_count:0,overdue_actions:[],recent_activity:[],results_visibility:'After Audit'};
function deferred(){let release!:()=>void;const promise=new Promise<void>(resolve=>{release=resolve});return {promise,release}}

test('published landing renders without waiting for bootstrap or downloading portal routes',async({page})=>{
 const session=deferred(),requested:string[]=[];
 page.on('request',request=>{if(request.resourceType()==='script')requested.push(request.url())});
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',async route=>{await session.promise;await route.fulfill({json:{message:guest}})});
 await page.route('**/api/method/ia_maturity.grc.public.site_content**',route=>route.fulfill({json:{message:{}}}));
 await page.goto('/grc-site');
 await expect(page.locator('.public-site')).toBeVisible();
 await expect(page.getByRole('heading',{name:/Stronger governance/})).toBeVisible();
 expect(requested.filter(url=>/frappe-react-sdk|WorkspaceShell|Assessment-|Dashboard-|Onboarding-|Guide-/.test(url))).toEqual([]);
 session.release();
 await page.getByRole('button',{name:'العربية',exact:true}).click();
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 await expect(page.locator('.public-site')).toBeVisible();
});

test('public copy survives a failed session lookup while private preview remains protected',async({page})=>{
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',route=>route.fulfill({status:401,json:{message:'Sign in again'}}));
 await page.route('**/api/method/ia_maturity.grc.public.site_content**',route=>route.fulfill({json:{message:{}}}));
 await page.goto('/grc-site');
 await expect(page.locator('.public-site')).toBeVisible();
 await page.goto('/grc-site?preview=PRIVATE-DRAFT');
 await expect(page.getByRole('alert')).toHaveText('Sign in again');
 await expect(page.locator('.public-site')).toHaveCount(0);
});

test('public page remains usable while the optional web-font stylesheet is delayed',async({page})=>{
 const fonts=deferred();let requested=false;
 await page.route('https://fonts.googleapis.com/**',async route=>{requested=true;await fonts.promise;await route.fulfill({contentType:'text/css',body:'/* delayed optional web fonts */'})});
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',route=>route.fulfill({json:{message:guest}}));
 await page.route('**/api/method/ia_maturity.grc.public.site_content**',route=>route.fulfill({json:{message:{}}}));
 await page.goto('/grc-site',{waitUntil:'domcontentloaded'});
 await expect.poll(()=>requested).toBe(true);
 await expect(page.getByRole('heading',{name:/Stronger governance/})).toBeVisible();
 await expect(page.getByRole('link',{name:'Sign in',exact:true})).toBeVisible();
 fonts.release();
});

for(const path of ['/signup','/login?signup=1']){
 test(`signup retains the existing-session sign-out gate at ${path}`,async({page})=>{
  const session=deferred();
  await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',async route=>{await session.promise;await route.fulfill({json:{message:auditor}})});
  await page.goto(path);
  await expect(page.getByRole('status')).toBeVisible();
  await expect(page.getByRole('button',{name:'Send code',exact:true})).toHaveCount(0);
  session.release();
  await expect(page.getByText('You are already signed in. Sign out before creating another account.')).toBeVisible();
  await expect(page.getByRole('button',{name:'Sign out to create an account',exact:true})).toBeVisible();
 });
}

test('private preview waits for session and preserves the server denial',async({page})=>{
 const session=deferred();let revisionRequests=0;
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',async route=>{await session.promise;await route.fulfill({json:{message:auditor}})});
 await page.route('**/api/method/ia_maturity.grc.api.site_content_revision**',route=>{revisionRequests++;return route.fulfill({status:403,json:{message:'Not permitted'}})});
 await page.goto('/grc-site?preview=PRIVATE-DRAFT');
 await expect(page.getByRole('status')).toBeVisible();
 expect(revisionRequests).toBe(0);
 session.release();
 await expect(page.getByRole('alert')).toContainText('Cannot preview this revision');
 expect(revisionRequests).toBe(1);
 await expect(page.locator('.public-site')).toHaveCount(0);
});

test('login serializes cookie-setting Guest responses before authentication and one fresh lookup',async({page})=>{
 await page.clock.install();
 const first=deferred(),authentication=deferred();let bootstrapRequests=0,authPosts=0;
 const events:string[]=[];
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',async route=>{
  bootstrapRequests++;
  const signedIn=route.request().headers().cookie?.includes('sid=authenticated');
  const message=signedIn?{enabled:true,kind:'ERP',home:'/app/home'}:guest;
  if(bootstrapRequests===1)await first.promise;
  events.push(signedIn?'authenticated-get':'guest-response');
  await route.fulfill({headers:{'Set-Cookie':'sid='+(signedIn?'authenticated':'Guest')+'; Path=/; SameSite=Lax'},json:{message}});
 });
 await page.route('**/api/method/login',async route=>{authPosts++;events.push('auth-post');await authentication.promise;await route.fulfill({headers:{'Set-Cookie':'sid=authenticated; Path=/; SameSite=Lax'},json:{message:'Logged In',home_page:'/app/home'}})});
 await page.route('**/app/home',route=>route.fulfill({contentType:'text/html',body:'<h1>ERP workspace</h1>'}));
 await page.goto('/login?staff=1');
 await page.getByLabel('Email or username',{exact:true}).fill('perf-erp@example.test');
 await page.getByLabel('Password',{exact:true}).fill('browser-test-placeholder');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page.getByRole('button',{name:'Sign in',exact:true})).toBeDisabled();
 expect(authPosts).toBe(0);expect(bootstrapRequests).toBe(1);
 first.release();
 await expect.poll(()=>authPosts).toBe(1);
 // Focus and timer events during the auth POST must not launch another Guest GET.
 await page.evaluate(()=>{window.dispatchEvent(new Event('focus'));document.dispatchEvent(new Event('visibilitychange'))});
 await page.clock.fastForward(60000);
 expect(bootstrapRequests).toBe(1);
 authentication.release();
 await expect(page.getByRole('heading',{name:'ERP workspace'})).toBeVisible();
 expect(bootstrapRequests).toBe(2);
 expect(events).toEqual(['guest-response','auth-post','authenticated-get']);
 expect((await page.context().cookies()).find(cookie=>cookie.name==='sid')?.value).toBe('authenticated');
});

test('session refresh pauses hidden tabs, resumes immediately and does not overlap',async({page})=>{
 await page.clock.install();
 const second=deferred();let requests=0,active=0,maxActive=0;
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',async route=>{
  requests++;active++;maxActive=Math.max(maxActive,active);
  if(requests===2)await second.promise;
  await route.fulfill({json:{message:guest}});active--;
 });
 await page.goto('/login?staff=1');
 await expect(page.getByRole('button',{name:'Sign in',exact:true})).toBeVisible();
 await expect.poll(()=>requests).toBe(1);
 await page.evaluate(()=>{Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'hidden'});document.dispatchEvent(new Event('visibilitychange'))});
 await page.clock.fastForward(90000);
 expect(requests).toBe(1);
 await page.evaluate(()=>{Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'visible'});document.dispatchEvent(new Event('visibilitychange'));window.dispatchEvent(new Event('focus'))});
 await expect.poll(()=>requests).toBe(2);
 await page.clock.fastForward(60000);
 expect(requests).toBe(2);expect(maxActive).toBe(1);
 second.release();
 await expect.poll(()=>active).toBe(0);
 await page.clock.fastForward(30000);
 await expect.poll(()=>requests).toBe(3);
});

test('a rejected authentication attempt resumes visible session revalidation',async({page})=>{
 let requests=0;
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',route=>{requests++;return route.fulfill({json:{message:guest}})});
 await page.route('**/api/method/login',route=>route.fulfill({status:401,json:{message:'Authentication rejected'}}));
 await page.goto('/login?staff=1');
 await page.getByLabel('Email or username',{exact:true}).fill('perf-erp@example.test');
 await page.getByLabel('Password',{exact:true}).fill('browser-test-placeholder');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page.getByRole('alert')).toHaveText('Authentication rejected');
 await expect(page.getByRole('button',{name:'Sign in',exact:true})).toBeEnabled();
 const before=requests;
 await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
 await expect.poll(()=>requests).toBe(before+1);
});

for(const entry of [
 {path:'/grc/auditor',button:'Sign out',target:'/login'},
 {path:'/signup',button:'Sign out to create an account',target:'/signup'},
]){
 test(`${entry.path} logout drains old authenticated cookie responses before clearing the session`,async({page})=>{
  const pending=deferred();let requests=0,logoutPosts=0,loggedOut=false;
  await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',async route=>{
   requests++;
   if(requests===2)await pending.promise;
   await route.fulfill({headers:{'Set-Cookie':'sid=authenticated; Path=/; SameSite=Lax'},json:{message:{...auditor,access_version:requests===1?'before':'changed'}}});
  });
  await page.route('**/api/method/ia_maturity.grc.api.dashboard**',route=>route.fulfill({json:{message:dashboard}}));
  await page.route('**/api/method/ia_maturity.grc.api.templates**',route=>route.fulfill({json:{message:[]}}));
  await page.route('**/api/method/logout',route=>{logoutPosts++;loggedOut=true;return route.fulfill({headers:{'Set-Cookie':'sid=Guest; Path=/; SameSite=Lax'},json:{message:'Logged Out'}})});
  await page.route('**'+entry.target,route=>loggedOut?route.fulfill({contentType:'text/html',body:'<h1>Signed out</h1>'}):route.fallback());
  await page.goto(entry.path);
  await expect(page.getByRole('button',{name:entry.button,exact:true})).toBeVisible();
  await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
  await expect.poll(()=>requests).toBe(2);
  await page.getByRole('button',{name:entry.button,exact:true}).click();
  expect(logoutPosts).toBe(0);
  pending.release();
  await expect(page.getByRole('heading',{name:'Signed out'})).toBeVisible();
  expect(logoutPosts).toBe(1);
  expect((await page.context().cookies()).find(cookie=>cookie.name==='sid')?.value).toBe('Guest');
 });
}

test('visible session revalidation detects changed access and returns to its server home',async({page})=>{
 let requests=0;
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',route=>{requests++;return route.fulfill({json:{message:{...auditor,access_version:requests===1?'original':'revoked',home:requests===1?'/grc/auditor':'/login?access=changed'}}})});
 await page.route('**/api/method/ia_maturity.grc.api.dashboard**',route=>route.fulfill({json:{message:dashboard}}));
 await page.route('**/api/method/ia_maturity.grc.api.templates**',route=>route.fulfill({json:{message:[]}}));
 await page.route('**/login?access=changed',route=>route.fulfill({contentType:'text/html',body:'<h1>Access updated</h1>'}));
 await page.goto('/grc/auditor');
 await expect(page.getByRole('heading',{name:'Customer portfolio',exact:true})).toBeVisible();
 await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
 await expect(page.getByRole('heading',{name:'Access updated'})).toBeVisible();
 expect(requests).toBe(2);
});

for(const kind of ['Customer','Auditor'] as const){
 test(`${kind} workspace preferences update lazy header controls and survive reload`,async({page})=>{
  const user='perf-preferences@example.test',home=kind==='Customer'?'/grc/customer':'/grc/auditor';
  let preferences={show_page_tour:false,show_help:false};
  await page.addInitScript(user=>localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(user)+':skip-auto','1'),user);
  await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',route=>route.fulfill({json:{message:{...auditor,kind,user,home,workspace_preferences:preferences}}}));
  await page.route('**/api/method/ia_maturity.grc.api.profile**',route=>route.fulfill({json:{message:{kind,email:user,full_name:'Performance Preferences',modified:'1',name_repair_fields:[],values:{},editable_fields:[],fields:[],time_zones:[],workspace_preferences:preferences,authenticator:{available:false,required:false,enrolled:false,can_enroll:false,policy:'Disabled',method:'OTP App'}}}}));
  await page.route('**/api/method/ia_maturity.grc.api.save_workspace_preferences**',route=>{
   preferences=route.request().postDataJSON().data;
   return route.fulfill({json:{message:preferences}});
  });
  await page.goto(home+'/profile');
  await page.getByRole('tab',{name:'Workspace preferences',exact:true}).click();
  for(const name of ['Show page tour button','Show Help button'])await page.getByRole('checkbox',{name,exact:true}).check();
  await page.getByRole('button',{name:'Save workspace preferences',exact:true}).click();
  await expect(page.getByRole('link',{name:'Help & guides',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Take page tour',exact:true})).toBeVisible();
  for(const name of ['Show page tour button','Show Help button'])await page.getByRole('checkbox',{name,exact:true}).uncheck();
  await page.getByRole('button',{name:'Save workspace preferences',exact:true}).click();
  await expect(page.getByRole('link',{name:'Help & guides',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Take page tour',exact:true})).toHaveCount(0);
  await page.reload();
  await page.getByRole('tab',{name:'Workspace preferences',exact:true}).click();
  await expect(page.getByRole('checkbox',{name:'Show Help button',exact:true})).not.toBeChecked();
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:'العربية',exact:true}).click();
  await expect(page.getByRole('checkbox',{name:'إظهار زر المساعدة',exact:true})).toBeVisible();
 });
}
