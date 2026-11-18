import {test, expect} from '@playwright/test';

const guest={enabled:true,kind:'Guest',home:'/login'};

for(const home of ['/app/home','/desk/home']) {
  test(`normal ERP login opens Desk when native destination is ${home}`,async({page})=>{
    let signedIn=false;
    await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',route=>route.fulfill({json:{message:signedIn?{enabled:true,kind:'ERP',home}:guest}}));
    await page.route('**/api/method/login',async route=>{
      signedIn=true;
      await route.fulfill({json:{message:'Logged In',home_page:home}});
    });
    await page.route('**/app/home',route=>route.fulfill({contentType:'text/html',body:'<h1>ERP workspace</h1>'}));
    await page.goto('/login?staff=1');
    await page.getByLabel('Email or username',{exact:true}).fill('erp-user@example.test');
    await page.getByLabel('Password',{exact:true}).fill('browser-test-placeholder');
    await page.getByRole('button',{name:'Sign in',exact:true}).click();
    // v3.0.1 deliberately normalizes non-GRC accounts to /app/home.
    await expect(page).toHaveURL(/\/app\/home$/);
    await expect(page.getByRole('heading',{name:'ERP workspace'})).toBeVisible();
  });
}

for(const failure of ['forbidden','malformed'] as const) {
  test(`login handles ${failure} session lookup without a JavaScript crash`,async({page})=>{
    let signedIn=false;
    await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',route=>route.fulfill(
      !signedIn?{json:{message:guest}}:failure==='forbidden'
        ?{status:403,json:{message:'Account access was denied by the server'}}
        :{json:{}}));
    await page.route('**/api/method/login',async route=>{
      signedIn=true;
      await route.fulfill({json:{message:'Logged In',home_page:'/app/home'}});
    });
    await page.goto('/login?staff=1');
    await page.getByLabel('Email or username',{exact:true}).fill('erp-user@example.test');
    await page.getByLabel('Password',{exact:true}).fill('browser-test-placeholder');
    await page.getByRole('button',{name:'Sign in',exact:true}).click();
    await expect(page.getByRole('alert')).toHaveText(failure==='forbidden'
      ?'Account access was denied by the server'
      :'Unable to load your account. Please sign in again or contact your administrator.');
    await expect(page.getByRole('button',{name:'Sign in',exact:true})).toBeEnabled();
    await expect(page).toHaveURL(/\/login\?staff=1$/);
  });
}
