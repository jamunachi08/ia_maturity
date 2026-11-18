import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
function fixture(action:string,email:string,sid?:string){
 return execFileSync('../../../env/bin/python',['../scripts/local_authenticator_fixture.py',action,email,...(sid?[sid]:[])],{encoding:'utf8'}).trim();
}
test('customer enrolls a native authenticator from profile and signs in with password plus OTP',async({page,context})=>{
 const email='grc-authenticator-'+Date.now().toString(36)+'@example.test';
 const credentials=JSON.parse(fixture('create',email));
 try{
  await page.goto('/login');await page.getByLabel('Email or username').fill(email);await page.getByLabel('Password',{exact:true}).fill(credentials.password);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page).toHaveURL(/\/grc\/customer$/);
  await page.goto('/grc/customer/profile');await page.getByRole('tab',{name:'Account security'}).click();
  await expect(page.getByLabel('First name',{exact:true})).toHaveCount(0);
  await page.getByLabel('Current password',{exact:true}).first().fill(credentials.password);
  const begin=page.waitForResponse(r=>r.url().includes('ia_maturity.grc.api.begin_authenticator')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Set up authenticator'}).click();
  expect((await begin).headers()['cache-control']).toContain('no-store');
  await expect(page.getByAltText('Authenticator setup QR code')).toBeVisible();
  const sid=(await context.cookies()).find(c=>c.name==='sid')!.value;
  await page.getByLabel('Authenticator code').fill(fixture('pending-code',email,sid));
  await page.getByRole('button',{name:'Activate authenticator'}).click();await expect(page).toHaveURL(/\/login\?mfa=1$/);
  await page.getByLabel('Email or username').fill(email);await page.getByLabel('Password',{exact:true}).fill(credentials.password);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.getByLabel('Authenticator code')).toBeVisible();
  await page.getByLabel('Authenticator code').fill(fixture('login-code',email));
  await page.getByRole('button',{name:'Verify and continue'}).click();await expect(page).toHaveURL(/\/grc\/customer$/);
  await page.goto('/grc/customer/profile');await page.getByRole('tab',{name:'Account security'}).click();
  await expect(page.getByText('Your authenticator is enrolled. Contact your administrator if you lose access.')).toBeVisible();
  await page.screenshot({path:'test-results/authenticator-enrolled.png',fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:'العربية',exact:true}).click();await page.setViewportSize({width:390,height:844});
  await expect(page.locator('html')).toHaveAttribute('dir','rtl');
  await expect.poll(async()=> (await page.locator('.sidebar').boundingBox())!.x).toBeGreaterThanOrEqual(390);
  await page.screenshot({path:'test-results/authenticator-arabic.png',fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:'English',exact:true}).click();
  await page.getByLabel('Current password',{exact:true}).fill(credentials.password);
  const replacement=credentials.password+'-next';
  await page.getByLabel('New password',{exact:true}).fill(replacement);
  await page.getByLabel('Confirm new password',{exact:true}).fill(replacement);
  await page.getByRole('button',{name:'Change password',exact:true}).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel('Email or username').fill(email);await page.getByLabel('Password',{exact:true}).fill(replacement);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByLabel('Authenticator code')).toBeVisible();
 }finally{fixture('cleanup',email)}
});
