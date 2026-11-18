import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';

const credentials=JSON.parse(readFileSync('../../../sites/grc.local/private/grc-local-credentials.json','utf8'));
test('built-in Administrator signs in through Frappe and retains ERP access',async({page})=>{
  await page.goto('/login');
  await page.getByLabel('Email or username',{exact:true}).fill('Administrator');
  await page.getByLabel('Password',{exact:true}).fill(credentials.Administrator);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/method/login')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  expect((await response).status()).toBe(200);
  await expect(page).toHaveURL(/\/(app|apps)(\/|$)/);
  const bootstrap=await page.request.get('/api/method/ia_maturity.grc.api.bootstrap');
  expect(bootstrap.status()).toBe(200);
  const session=(await bootstrap.json()).message;
  expect(session.kind).toBe('ERP');
  expect(session.home).not.toMatch(/^\/grc\//);
  expect((await page.request.get('/app')).status()).toBe(200);
  expect((await page.request.get('/api/method/frappe.auth.get_logged_user')).status()).toBe(200);
  await page.goto('/grc/auditor');
  await expect(page).toHaveURL(/\/(app|apps)(\/|$)/);
});
