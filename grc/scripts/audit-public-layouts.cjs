/** Read-only public-page layout audit on disposable grc.local (port 8005). */
const {chromium}=require('playwright'),fs=require('fs'),path=require('path');
const output=path.resolve(__dirname,'../../../../sites/grc.local/private/layout-review');
(async()=>{fs.mkdirSync(output,{recursive:true});const browser=await chromium.launch(),page=await browser.newPage(),report=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
const routes=['/login','/signup','/update-password','/onboarding','/grc/demo/customer','/grc/demo/auditor',...['','services','catalogue','frameworks','about','resources','faq','contact','privacy','terms'].map(x=>'/grc-site/'+x)];
let index=0;for(const route of routes.filter(route=>!process.argv[2]||route.includes(process.argv[2]))){for(const [mode,width,lang] of [['desktop',1440,'en'],['mobile',390,'en'],['rtl',390,'ar']]){
 await page.setViewportSize({width,height:1000});await page.goto('http://127.0.0.1:8005'+route);await page.evaluate(lang=>localStorage.setItem('grc-language',lang),lang);await page.reload();await page.locator('.loading').waitFor({state:'hidden',timeout:15000}).catch(()=>{});await page.waitForTimeout(150);
 const file=(process.argv[2]?'public-recheck-':'public-')+index+'-'+mode+'.png';await page.screenshot({path:path.join(output,file),fullPage:true});report.push({route,mode,file,...await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,direction:document.documentElement.dir,title:document.querySelector('h1,h2')?.textContent}))});fs.writeFileSync(path.join(output,process.argv[2]?'public-recheck.json':'public.json'),JSON.stringify({report,errors},null,2));
}index++}await browser.close();console.log(report.length+' views, '+report.filter(x=>x.overflow).length+' overflow, '+errors.length+' errors');})();
