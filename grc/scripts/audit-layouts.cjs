/** Read-only visual audit against the disposable grc.local site on port 8005.
 * Manager presentation uses admin demo data with a manager bootstrap capability set.
 * This exercises layout, not permission enforcement. Never run against production.
 */
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),{execFileSync}=require('child_process');
const root=path.resolve(__dirname,'..'),bench=path.resolve(root,'../../..');
const credentials=JSON.parse(fs.readFileSync(path.join(bench,'sites/grc.local/private/grc-local-credentials.json'),'utf8'));
const output=path.join(bench,'sites/grc.local/private/layout-review');fs.mkdirSync(output,{recursive:true});
const origin='http://127.0.0.1:8005';
const roles=[['customer','customer@alpha.example.test'],['auditor','auditor@grc.example.test'],['reviewer','reviewer@grc.example.test'],['admin','admin@grc.example.test'],['manager','admin@grc.example.test']];
(async()=>{const browser=await chromium.launch({headless:true});
for(const [role,email] of roles.filter(([role])=>!process.argv[2]||process.argv[2]==='all'||process.argv[2]===role)){
 const report=[],context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 if(role==='manager')await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',async route=>{const response=await route.fetch(),json=await response.json();Object.assign(json.message,{is_admin:false,staff_roles:['GRC Manager'],can_configure_scope:true,can_operations:true,can_site_content:false});await route.fulfill({response,json})});
 await page.addInitScript(email=>{if(!localStorage.getItem('grc-language'))localStorage.setItem('grc-language','en');localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(email)+':skip-auto','1')},email);
 await page.goto(origin+'/login');await page.getByLabel('Email or username').fill(email);await page.getByLabel('Password',{exact:true}).fill(credentials[email]);await page.getByRole('button',{name:'Sign in',exact:true}).click();
 if(role!=='customer'){await page.getByLabel('Authenticator code').waitFor();await page.screenshot({path:path.join(output,role+'-mfa.png'),fullPage:true});const otp=execFileSync(path.join(bench,'env/bin/python'),[path.join(root,'../scripts/local_test_otp.py'),email],{encoding:'utf8'}).trim();await page.getByLabel('Authenticator code').fill(otp);await page.getByRole('button',{name:'Verify and continue'}).click()}
 await page.locator('.sidebar nav a').first().waitFor();
 const base=role==='customer'?'/grc/customer':'/grc/auditor';
 const routes=new Set(await page.locator('.sidebar a[href^="/grc/"]').evaluateAll(xs=>xs.map(x=>x.getAttribute('href'))));routes.add(base+'/guide');
 async function ready(){await page.locator('.main-content').waitFor();await page.locator('.main-content .loading').waitFor({state:'hidden',timeout:15000}).catch(()=>{});await page.waitForTimeout(180)}
 for(const route of [...routes]){
  if(!/(assessments|templates|customers|organization|onboarding)$/.test(route))continue;
  await page.goto(origin+route);await ready();const links=await page.locator('.main-content a[href^="'+route+'/"]').evaluateAll(xs=>xs.map(x=>x.getAttribute('href')));
  for(const href of [...links.slice(0,2),...links.slice(-2)])routes.add(href);
 }
 if(role==='admin')routes.add(base+'/admin/templates/new');
 if(process.argv[3]==='tabs'){for(const route of [...routes])if(!/(profile|oversight|organization\/[^/]+|customers\/[^/]+)$/.test(route))routes.delete(route)}
 if(process.argv[4])for(const route of [...routes])if(!route.includes(process.argv[4]))routes.delete(route);
 let index=0;
 async function snapshot(route,mode,suffix=''){
  const metrics=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,title:document.querySelector('main h1')?.textContent,language:document.documentElement.lang,direction:document.documentElement.dir,alerts:[...document.querySelectorAll('[role=alert]')].map(x=>x.textContent),outside:[...document.querySelectorAll('main button,main input,main textarea,main .panel')].filter(x=>{const b=x.getBoundingClientRect();return b.width&&(b.right>innerWidth+1||b.left< -1)&&!x.closest('.table-scroll,.tabs,[style*="overflow"]')}).slice(0,8).map(x=>({tag:x.tagName,class:x.className,text:x.textContent?.slice(0,80)}))}));
  const file=role+(process.argv[3]==='tabs'?'-tabs':'')+(process.argv[4]?'-recheck':'')+'-'+index+'-'+mode+suffix+'.png';await page.screenshot({path:path.join(output,file),fullPage:true});report.push({role,route,mode,view:suffix||'page',file,...metrics});fs.writeFileSync(path.join(output,role+(process.argv[3]==='tabs'?'-tabs':'')+(process.argv[4]?'-recheck':'')+'.json'),JSON.stringify({report,errors},null,2));
 }
 for(const route of routes){for(const [mode,width,lang] of [['desktop',1440,'en'],['mobile',390,'en'],['rtl',390,'ar']]){
  await page.setViewportSize({width,height:1000});await page.evaluate(lang=>localStorage.setItem('grc-language',lang),lang);await page.goto(origin+route);await ready();
  const normal=page.locator('[data-focus-toggle]');if(await normal.count())await normal.first().click();
  await snapshot(route,mode);
  if(process.argv[3]==='tabs'){const tabs=page.locator('.main-content .tabs button,.main-content .oversight-tabs[role=tablist] button');for(let i=1;i<await tabs.count();i++){await tabs.nth(i).click();await ready();await snapshot(route,mode,'-tab-'+i)}}
  if(route.endsWith('/audit-packages')){const select=page.getByRole('combobox').first();await select.click();const options=page.getByRole('option');if(await options.count()>1){await options.nth(1).click();await ready();await snapshot(route,mode,'-configured')}else await page.keyboard.press('Escape')}
 }
 index++}
 await context.close();console.log(role+': '+routes.size+' routes, '+report.length+' views, '+report.filter(x=>x.overflow).length+' overflow, '+errors.length+' page errors');
}
await browser.close();})();
