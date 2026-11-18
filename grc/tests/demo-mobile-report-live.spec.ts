import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdirSync} from 'node:fs';

// Targeted visual recheck of existing released records after the CSS-only fix.
test.skip(process.env.GRC_RUN_DEMO_MOBILE!=='1'||!process.env.GRC_DEMO_RUN,'Requires a completed guarded demo cycle.');
test.use({trace:'off',video:'off',viewport:{width:390,height:844}});
const run=process.env.GRC_DEMO_RUN||'';
for(const kind of ['ia','grc'])test(`released ${kind} customer report on Arabic mobile keeps actions without blank PDF frame`,async({page})=>{
 const email=`grc-journey-${run}-invited-${kind}@example.test`;
 await page.addInitScript(email=>{localStorage.setItem('grc-language','en');localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(email)+':skip-auto','1')},email);
 await page.goto('/login');
 await page.getByLabel('Email',{exact:true}).fill(email);
 await page.getByRole('button',{name:'Send code',exact:true}).click();
 await expect(page.getByLabel('Verification code',{exact:true})).toBeVisible();
 const result=JSON.parse(execFileSync('/home/frappe/frappe-bench/env/bin/python',['../scripts/demo_cycle_fixture.py','code',run,email],{encoding:'utf8',stdio:['ignore','pipe','pipe']}));
 await page.getByLabel('Verification code',{exact:true}).fill(result.code);
 await page.getByRole('button',{name:'Verify and continue',exact:true}).click();
 await expect(page).toHaveURL(/\/grc\/customer$/);
 const dashboard=await page.evaluate(async()=>{const response=await fetch('/api/method/ia_maturity.grc.api.dashboard',{credentials:'same-origin'});return response.json()});
 const name=dashboard.message.assessments[0].name;
 await page.goto('/grc/customer/assessments/'+encodeURIComponent(name));
 await expect(page.getByRole('link',{name:'Download PDF',exact:true})).toBeVisible();
 await expect(page.getByTitle('Report preview',{exact:true})).toBeHidden();
 await page.getByRole('button',{name:'العربية',exact:true}).click();
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 await expect(page.getByRole('link',{name:'تنزيل PDF',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'إرسال التقرير بالبريد',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 mkdirSync('../../../diagnostics/demo-cycle-20261112/final-screenshots',{recursive:true});
 await page.screenshot({path:`../../../diagnostics/demo-cycle-20261112/final-screenshots/demo-${run}-${kind}-report-mobile-fixed.png`,fullPage:true});
});
