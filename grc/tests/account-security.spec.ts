import {test,expect,Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
const credentials=JSON.parse(readFileSync('../../../sites/grc.local/private/grc-local-credentials.json','utf8'));
function fixture(action:string,email:string){return execFileSync('../../../env/bin/python',['../scripts/local_authenticator_fixture.py',action,email],{encoding:'utf8'}).trim()}
async function login(page:Page,email:string,password:string,mfa:boolean,admin=false){
 await page.goto('/login');await page.getByLabel('Email or username').fill(email);await page.getByLabel('Password',{exact:true}).fill(password);
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 if(mfa){
  await expect(page.getByLabel('Authenticator code')).toBeVisible();
  const code=admin?execFileSync('../../../env/bin/python',['../scripts/local_test_otp.py',email],{encoding:'utf8'}).trim():fixture('login-code',email);
  await page.getByLabel('Authenticator code').fill(code);await page.getByRole('button',{name:'Verify and continue'}).click();
 }
 await expect(page).toHaveURL(/\/grc\/(customer|auditor)$/);
}
test('admin enables and disables customer and auditor MFA and revokes active sessions',async({page,browser})=>{
 test.setTimeout(90000);
 const admin='admin@grc.example.test';
 await login(page,admin,credentials[admin],true,true);
 for(const kind of ['customer','auditor']){
  const email='grc-authenticator-'+Date.now().toString(36)+'@example.test';
  const account=JSON.parse(fixture(kind==='auditor'?'create-auditor':'create',email));
  const context=await browser.newContext(),user=await context.newPage();
  try{
   await login(user,email,account.password,kind==='auditor');
   await page.goto('/grc/auditor/admin/security');
   await page.getByLabel('Search',{exact:true}).fill(email);
   await expect(page.getByRole('cell',{name:email,exact:true})).toBeVisible();
   for(const policy of ['Disabled','Required']){
    await page.getByRole('button',{name:'Edit security',exact:true}).click();
    const dialog=page.getByRole('dialog',{name:'MFA policy',exact:true});
    await dialog.getByRole('combobox',{name:'MFA policy',exact:true}).click();
    await page.getByRole('option',{name:policy,exact:true}).click();
    await dialog.getByLabel('Your current password').fill(credentials[admin]);
    await dialog.getByRole('button',{name:'Save security policy',exact:true}).click();
    await expect(dialog).toHaveCount(0);
    await user.reload();await expect(user).toHaveURL(/\/login/);
    await login(user,email,account.password,policy==='Required');
    if(kind==='customer'&&policy==='Disabled'){
     await user.goto('/grc/customer/profile');await user.getByRole('tab',{name:'Account security'}).click();
     await expect(user.getByText('Authenticator setup is disabled by your GRC administrator.')).toBeVisible();
     await expect(user.getByRole('button',{name:'Set up authenticator'})).toHaveCount(0);
    }
   }
   await page.screenshot({path:'test-results/admin-account-security-'+kind+'.png',fullPage:true,animations:'disabled'});
  }finally{await context.close();fixture('cleanup',email)}
 }
});
