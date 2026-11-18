import {test,expect,Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
const credentials=JSON.parse(readFileSync('../../../sites/grc.local/private/grc-local-credentials.json','utf8'));
async function login(page:Page,email='customer@alpha.example.test'){
 await page.goto('/login');await page.getByLabel('Email or username').fill(email);await page.getByLabel('Password',{exact:true}).fill(credentials[email]);
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 if(email.includes('@grc.example.test')){
  await expect(page.getByLabel('Authenticator code')).toBeVisible();
  const otp=execFileSync('../../../env/bin/python',['../scripts/local_test_otp.py',email],{encoding:'utf8'}).trim();
  await page.getByLabel('Authenticator code').fill(otp);await page.getByRole('button',{name:'Verify and continue'}).click();
 }
 await expect(page).toHaveURL(/\/grc\/(customer|auditor)$/);
}
test('headline cards preserve group filters and dropdowns support keyboard and RTL',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await login(page);
 for(const [label,group] of [['In progress','in_progress'],['Awaiting review','awaiting_review'],['Overdue','overdue'],['Reports released','released']]){
  await page.goto('/grc/customer');
  await page.getByRole('link',{name:new RegExp('^'+label+':')}).click();
  await expect(page).toHaveURL(new RegExp('assessments\\?group='+group));
  await expect(page.locator('.active-filter')).toContainText(label);
  await page.reload();await expect(page.locator('.active-filter')).toContainText(label);
  await expect(page.getByText('Safa Financial Services')).toHaveCount(0);
 }
 const status=page.getByRole('combobox',{name:'Status',exact:true});
 await status.click();await expect(page.getByRole('listbox')).toBeVisible();
 await page.screenshot({path:'test-results/styled-dropdown.png',fullPage:true,animations:'disabled'});
 await page.getByRole('option',{name:'Draft',exact:true}).click();
 await expect(page).toHaveURL(/state=Draft/);await expect(page.locator('.active-filter')).toHaveCount(0);
 await status.focus();await page.keyboard.press('ArrowDown');await expect(page.getByRole('option',{name:'Draft',exact:true})).toBeFocused();await page.keyboard.press('End');await expect(page.getByRole('option',{name:'Report Released',exact:true})).toBeFocused();await page.keyboard.press('Enter');
 await expect(page).toHaveURL(/state=Report\+Released/);
 await page.getByRole('button',{name:'العربية',exact:true}).click();
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('combobox',{name:'الحالة',exact:true}).click();
 await expect(page.getByRole('listbox')).toHaveAttribute('dir','rtl');
 const bounds=await page.getByRole('listbox').boundingBox();expect(bounds!.x).toBeGreaterThanOrEqual(0);expect(bounds!.x+bounds!.width).toBeLessThanOrEqual(390);
 await page.screenshot({path:'test-results/styled-dropdown-arabic.png',fullPage:false,animations:'disabled'});
 await page.keyboard.press('Escape');
 await expect(page.getByRole('listbox')).toHaveCount(0);
 expect(errors).toEqual([]);
});
test('customer profile saves allowed fields and keeps login identity read-only',async({page})=>{
 await login(page);await page.getByRole('link',{name:'My profile',exact:true}).click();
 await expect(page).toHaveURL(/\/profile$/);
 await expect(page.getByLabel('Email',{exact:true})).toHaveAttribute('readonly','');
 const phone=page.getByLabel('Phone number',{exact:true}),before=await phone.inputValue();
 try{
  await phone.fill('+49 123 456 789');
  const savedProfile=page.waitForResponse(r=>r.url().includes('ia_maturity.grc.api.save_profile')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Save profile',exact:true}).click();await savedProfile;
  await page.reload();await expect(page.getByLabel('Phone number',{exact:true})).toHaveValue('+49 123 456 789');
  await expect(page.getByLabel('Current password')).toHaveCount(0);
  await page.getByRole('tab',{name:'Account security'}).click();
  await expect(page.getByLabel('First name',{exact:true})).toHaveCount(0);
  await expect(page.getByLabel('Current password')).toHaveCount(2);
  await expect(page.getByLabel('Confirm new password')).toBeVisible();
  await page.screenshot({path:'test-results/profile-page.png',fullPage:true,animations:'disabled'});
 }finally{
  await page.getByRole('tab',{name:'Personal details'}).click();
  await page.getByLabel('Phone number',{exact:true}).fill(before);
  const saved=page.waitForResponse(r=>r.url().includes('ia_maturity.grc.api.save_profile')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Save profile',exact:true}).click();await saved;
 }
});
test('assigned customer card opens customer details and modal dropdown closes without closing dialog',async({page})=>{
 await login(page,'auditor@grc.example.test');
 await page.getByRole('link',{name:/^Assigned customers:/}).click();
 await expect(page).toHaveURL(/\/customers\/Al%20Noor%20Industries$/);
 await expect(page.getByRole('heading',{name:'Al Noor Industries'})).toBeVisible();
 await page.goto('/login'); // Existing staff session returns to its workspace.
 await page.getByRole('button',{name:'Sign out'}).click();
 await login(page,'admin@grc.example.test');
 await page.getByRole('link',{name:'Customer assignments',exact:true}).click();
 await page.getByRole('combobox',{name:'Organization',exact:true}).click();
 await page.getByRole('option',{name:'Al Noor Industries',exact:true}).click();
 await page.getByRole('button',{name:'Assign customer',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Customer assignment',exact:true});
 await dialog.getByRole('combobox',{name:'Responsibility',exact:true}).click();
 await expect(page.getByRole('option',{name:'Reviewer',exact:true})).toBeVisible();
 await page.keyboard.press('Escape');await expect(dialog).toBeVisible();await expect(page.getByRole('listbox')).toHaveCount(0);
 await dialog.getByRole('button',{name:'Close',exact:true}).click();
});
test('admin policy locks profile fields in the UI and rejects direct saves',async({page,browser})=>{
 await login(page,'admin@grc.example.test');await page.goto('/grc/auditor/admin/settings');
 const checkbox=page.getByRole('checkbox',{name:'First name',exact:true});
 const original=await checkbox.isChecked();
 const customerContext=await browser.newContext(),customer=await customerContext.newPage();
 try{
  await checkbox.uncheck();
  const saved=page.waitForResponse(r=>r.url().includes('ia_maturity.grc.api.save_settings')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Save changes',exact:true}).click();expect((await saved).status()).toBe(200);
  await login(customer);await customer.getByRole('link',{name:'My profile',exact:true}).click();
  await expect(customer.getByLabel('First name',{exact:true})).toBeDisabled();
  const denied=await customer.evaluate(async()=>{
   const r=await fetch('/api/method/ia_maturity.grc.api.save_profile',{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':(window as any).csrf_token},body:JSON.stringify({data:{first_name:'Blocked update'}})});return r.status;
  });
  expect(denied).toBe(403);
 }finally{
  await page.goto('/grc/auditor/admin/settings');await page.getByRole('checkbox',{name:'First name',exact:true}).setChecked(original);
  const saved=page.waitForResponse(r=>r.url().includes('ia_maturity.grc.api.save_settings')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Save changes',exact:true}).click();await saved;
  await customerContext.close();
 }
});


test('an existing session cannot masquerade as a new verified signup',async({page})=>{
 await login(page);await page.goto('/signup');
 await expect(page.getByText('You are already signed in. Sign out before creating another account.')).toBeVisible();
 await expect(page.getByLabel('Email',{exact:true})).toBeHidden();
 await page.getByRole('button',{name:'Sign out to create an account'}).click();
 await expect(page.getByLabel('Email',{exact:true})).toBeVisible();
});
