import {test,expect,Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
const credentials=JSON.parse(readFileSync('../../../sites/grc.local/private/grc-local-credentials.json','utf8'));
async function staffLogin(page:Page,email:string){
 await page.goto('/login');await page.getByLabel('Email or username').fill(email);await page.getByLabel('Password',{exact:true}).fill(credentials[email]);
 await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.getByLabel('Authenticator code')).toBeVisible();
 const otp=execFileSync('/home/frappe/frappe-bench/env/bin/python',['../scripts/local_test_otp.py',email],{encoding:'utf8'}).trim();
 await page.getByLabel('Authenticator code').fill(otp);await page.getByRole('button',{name:'Verify and continue'}).click();
 await expect(page).toHaveURL(/\/grc\/auditor$/);
}
test('assigned auditor sees only assigned customer and no administration',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await staffLogin(page,'auditor@grc.example.test');
 await expect(page.getByRole('heading',{name:'My review queue'})).toBeVisible();
 await expect(page.getByText('Safa Financial Services')).toHaveCount(0);
 await expect(page.getByRole('link',{name:'Customer assignments',exact:true})).toHaveCount(0);
 await page.screenshot({path:'test-results/auditor-dashboard.png',fullPage:true});
 await page.goto('/grc/auditor/admin/settings');await expect(page).toHaveURL(/\/grc\/auditor$/);
 expect(errors).toEqual([]);
});
test('unassigned auditor has an empty queue',async({page})=>{
 await staffLogin(page,'unassigned@grc.example.test');
 await expect(page.getByRole('heading',{name:'No customers assigned'})).toBeVisible();
});
test('admin assignment controls, settings and published templates',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await staffLogin(page,'admin@grc.example.test');
 await page.getByRole('link',{name:'Customer assignments',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Customer assignments',exact:true})).toBeVisible();
 await page.getByRole('combobox',{name:'Organization',exact:true}).click();
 await page.getByRole('option',{name:'Al Noor Industries',exact:true}).click();
 await expect(page.getByRole('cell',{name:'auditor@grc.example.test',exact:true})).toBeVisible();
 await expect(page.getByRole('cell',{name:'reviewer@grc.example.test',exact:true})).toBeVisible();
 await page.screenshot({path:'test-results/admin-assignments.png',fullPage:true});
 await page.getByRole('link',{name:'Questionnaire templates',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Questionnaire templates',exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Open',exact:true}).first().click();
 await expect(page).toHaveURL(/\/grc\/auditor\/admin\/templates\//);
 await expect(page.getByText('Published — read only')).toBeVisible();
 await page.getByRole('link',{name:'Customer preview',exact:true}).click();
 await expect(page.getByText('Preview mode')).toBeVisible();
 await expect(page.locator('.iam-questionnaire .question-card').first()).toBeVisible({timeout:15000});
 await expect(page.getByText('Current score')).toBeVisible();
 await page.getByRole('link',{name:'Questionnaire templates',exact:true}).click();
 await page.getByRole('link',{name:'Settings',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Customer results before report release',exact:true})).toBeVisible();
 await expect(page.getByRole('radio',{name:/Status only/})).toBeVisible();
 await page.screenshot({path:'test-results/admin-settings.png',fullPage:true});
 expect(errors).toEqual([]);
});
