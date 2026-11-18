import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
const credentials=JSON.parse(readFileSync('../../../sites/grc.local/private/grc-local-credentials.json','utf8'));
test('admin can set a role policy and select an individual administrator override',async({page})=>{
 const admin='admin@grc.example.test';await page.addInitScript(user=>localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(user)+':skip-auto','1'),admin);
 await page.goto('/login');await page.getByLabel('Email or username').fill(admin);await page.getByLabel('Password',{exact:true}).fill(credentials[admin]);await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page.getByLabel('Authenticator code')).toBeVisible();const otp=execFileSync('../../../env/bin/python',['../scripts/local_test_otp.py',admin],{encoding:'utf8'}).trim();await page.getByLabel('Authenticator code').fill(otp);await page.getByRole('button',{name:'Verify and continue'}).click();await expect(page).toHaveURL(/\/grc\/auditor$/);
 await page.goto('/grc/auditor/admin/security');const roleRow=page.getByRole('row').filter({has:page.getByRole('cell',{name:'GRC Customer',exact:true})});await expect(roleRow).toBeVisible();
 const setRole=async(policy:string)=>{await roleRow.getByRole('button',{name:'Edit role policy'}).click();const modal=page.getByRole('dialog',{name:'MFA role policy'});await modal.getByRole('combobox',{name:'MFA policy'}).click();await page.getByRole('option',{name:policy,exact:true}).click();await modal.getByLabel('Your current password').fill(credentials[admin]);await modal.getByRole('button',{name:'Save security policy'}).click();await expect(modal).toHaveCount(0);await expect(roleRow.getByRole('cell',{name:policy,exact:true})).toBeVisible()};
 try{await setRole('Disabled')}finally{await setRole('Default')}
 await page.getByLabel('Search',{exact:true}).fill(admin);const userRow=page.getByRole('row').filter({has:page.getByRole('cell',{name:admin,exact:true})});await userRow.getByRole('button',{name:'Edit security'}).click();const dialog=page.getByRole('dialog',{name:'MFA policy'});await dialog.getByRole('combobox',{name:'MFA policy'}).click();await expect(page.getByRole('option',{name:'Disabled',exact:true})).toBeVisible();await page.keyboard.press('Escape');
 await dialog.getByRole('button',{name:'Close'}).click();await page.getByRole('button',{name:'العربية'}).click();await expect(page.getByRole('heading',{name:'المصادقة الثنائية حسب دور GRC'})).toBeVisible();
});

test('an administrator can sign in without an authenticator when individually disabled',async({page,browser})=>{
 const admin='admin@grc.example.test', email='grc-authenticator-'+Date.now().toString(36)+'@example.test';
 const fixture=(action:string)=>execFileSync('../../../env/bin/python',['../scripts/local_authenticator_fixture.py',action,email],{encoding:'utf8'}).trim();
 const account=JSON.parse(fixture('create-admin'));const context=await browser.newContext();const target=await context.newPage();
 try {
  await page.addInitScript(user=>localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(user)+':skip-auto','1'),admin);
  await page.goto('/login');await page.getByLabel('Email or username').fill(admin);await page.getByLabel('Password',{exact:true}).fill(credentials[admin]);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.getByLabel('Authenticator code')).toBeVisible();
  const otp=execFileSync('../../../env/bin/python',['../scripts/local_test_otp.py',admin],{encoding:'utf8'}).trim();await page.getByLabel('Authenticator code').fill(otp);await page.getByRole('button',{name:'Verify and continue'}).click();await expect(page).toHaveURL(/\/grc\/auditor$/);
  await page.goto('/grc/auditor/admin/security');await page.getByLabel('Search',{exact:true}).fill(email);const row=page.getByRole('row').filter({has:page.getByRole('cell',{name:email,exact:true})});await expect(row).toBeVisible();await row.getByRole('button',{name:'Edit security'}).click();const dialog=page.getByRole('dialog',{name:'MFA policy'});await dialog.getByRole('combobox',{name:'MFA policy'}).click();await page.getByRole('option',{name:'Disabled',exact:true}).click();await dialog.getByLabel('Your current password').fill(credentials[admin]);await dialog.getByRole('button',{name:'Save security policy'}).click();await expect(dialog).toHaveCount(0);
  await target.goto('/login');await target.getByLabel('Email or username').fill(email);await target.getByLabel('Password',{exact:true}).fill(account.password);await target.getByRole('button',{name:'Sign in',exact:true}).click();await expect(target).toHaveURL(/\/grc\/auditor$/);await expect(target.getByLabel('Authenticator code')).toHaveCount(0);
 } finally {await context.close();fixture('cleanup')}
});
