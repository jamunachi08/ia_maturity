import {test, expect} from '@playwright/test';

test('password sign-in submits Administrator to Frappe and displays the server decision', async({page})=>{
  const identifiers: string[]=[];
  // Keep this browser regression independent of real Administrator credentials.
  await page.route('**/api/method/login',async route=>{
    identifiers.push(route.request().postDataJSON().usr);
    await route.fulfill({status:401,contentType:'application/json',body:JSON.stringify({message:'Test authentication rejected by server'})});
  });
  await page.goto('/login');
  const identifier=page.getByLabel('Email or username',{exact:true});
  await expect(identifier).toHaveAttribute('type','text');
  await expect(identifier).toHaveAttribute('autocomplete','username');
  await identifier.fill('Administrator');
  await page.getByLabel('Password',{exact:true}).fill('browser-test-placeholder');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByText('Test authentication rejected by server')).toBeVisible();
  expect(identifiers).toEqual(['Administrator']);
  await page.getByRole('button',{name:'العربية',exact:true}).click();
  await expect(page.getByLabel('البريد الإلكتروني أو اسم المستخدم',{exact:true})).toHaveValue('Administrator');
});

test('email-code signup and recovery retain email validation',async({page})=>{
  for(const mode of ['signup','email','forgot']){
    await page.goto(mode==='signup'?'/signup':'/login');
    if(mode==='email') await page.getByRole('button',{name:'Email code',exact:true}).click();
    if(mode==='forgot') await page.getByRole('button',{name:'Forgot password?',exact:true}).click();
    const email=page.getByLabel('Email',{exact:true});
    await expect(email).toHaveAttribute('type','email');
    await email.fill('Administrator');
    expect(await email.evaluate((input:HTMLInputElement)=>input.validity.typeMismatch)).toBeTruthy();
    await email.fill('tester@example.test');
    expect(await email.evaluate((input:HTMLInputElement)=>input.validity.valid)).toBeTruthy();
  }
});
