import {test,expect,Page} from '@playwright/test';
async function fixture(page:Page,kind='Customer',editable=true,native='supported',long=false){
 await page.addInitScript(mode=>{
  localStorage.setItem('grc-language','en');if(mode==='real')return;const w=window as any;w.requests=0;w.exits=0;let element:Element|null=null;
  Object.defineProperty(document,'fullscreenEnabled',{get:()=>mode!=='unsupported'});
  Object.defineProperty(document,'fullscreenElement',{get:()=>element});
  // The DOM fullscreen method must capture its receiving element.
  // eslint-disable-next-line typescript/no-this-alias
  Element.prototype.requestFullscreen=async function(){w.requests++;if(mode==='denied')throw new Error('Denied');element=this;document.dispatchEvent(new Event('fullscreenchange'))};
  document.exitFullscreen=async()=>{w.exits++;element=null;document.dispatchEvent(new Event('fullscreenchange'))};
 },native);
 const doc:any={name:'FOCUS',entity:'Focus customer',template:'Default',modified:'v1',docstatus:0,editable,results_visible:false,released:false,review_actions:[],overall_maturity_visibility:'Completed sections only',questions:[1,2].map(n=>({question_code:'Q'+n,section_code:'S'+n,section_title:'Domain '+n,question_text:'Question '+n,option_a:'Ad hoc',option_b:'Basic',option_c:'Established',option_d:'Leading',selected_option:'',allow_comment:0,allow_attachment:0}))};
 if(long)doc.questions=Array.from({length:12},(_,i)=>({...doc.questions[0],question_code:'Q'+(i+1),section_code:i===11?'S2':'S1',section_title:i===11?'Domain 2':'Domain 1',question_text:'Question '+(i+1)+' '+('Long question detail '.repeat(12)),option_a:'First option '+('Detailed practice description '.repeat(18)),option_b:'Second option '+('Detailed practice description '.repeat(18)),option_c:'Third option '+('Detailed practice description '.repeat(18)),option_d:'Final option '+('LongUnbrokenAnswerText'.repeat(20)),allow_na:1}));
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind,user:'focus@example.test',home:kind==='Customer'?'/grc/customer':'/grc/auditor',organizations:[],workspace_preferences:{show_page_tour:false,show_help:false}}}}));
 await page.route('**/api/method/ia_maturity.grc.api.assessment?**',r=>r.fulfill({json:{message:doc}}));
 await page.route('**/api/method/ia_maturity.grc.api.activity**',r=>r.fulfill({json:{message:[]}}));
 await page.route('**/api/method/ia_maturity.grc.api.save_assessment',r=>{const answers=r.request().postDataJSON().answers;doc.questions.forEach((q:any)=>q.selected_option=answers[q.question_code]?.selected_option||'');return r.fulfill({json:{message:doc}})});
 await page.route('**/api/method/ia_maturity.grc.api.submit_assessment',r=>{doc.editable=false;doc.docstatus=1;return r.fulfill({json:{message:doc}})});
 await page.goto((kind==='Customer'?'/grc/customer':'/grc/auditor')+'/assessments/FOCUS');
 await expect(page.locator('.question-heading h3').first()).toBeVisible();return doc;
}
test('automatic focus requests native fullscreen on answering and preserves answers in normal view',async({page})=>{
 await fixture(page);await expect(page.locator('.assessment-focus-active')).toBeVisible();await expect(page.locator('.sidebar')).toBeHidden();await expect(page.locator('.report-disclosure')).toBeHidden();expect(await page.evaluate(()=>(window as any).requests)).toBe(0);
 await page.locator('input[value=C]').check();await expect.poll(()=>page.evaluate(()=>(window as any).requests)).toBe(1);
 await page.getByRole('button',{name:'Next section'}).click();await expect(page.getByText('Question 2',{exact:true})).toBeVisible();expect(await page.evaluate(()=>(window as any).requests)).toBe(1);
 await page.getByRole('button',{name:'Normal view',exact:true}).click();await expect(page.locator('.assessment-focus-active')).toHaveCount(0);await expect(page.locator('.sidebar')).toBeVisible();expect(await page.evaluate(()=>(window as any).exits)).toBe(1);
 await page.getByRole('button',{name:'Previous section'}).click();await expect(page.locator('input[value=C]')).toBeChecked();await page.getByRole('button',{name:'Save',exact:true}).click();await expect.poll(()=>page.evaluate(()=>document.querySelector('.save-state')?.textContent)).toMatch(/Saved|saved/);await page.reload();await expect(page.locator('.assessment-focus-active')).toHaveCount(0);await expect(page.locator('input[value=C]')).toBeChecked();
 await page.getByRole('button',{name:'Full screen',exact:true}).click();await expect(page.locator('.assessment-focus-active')).toBeVisible();await page.screenshot({path:'test-results/focus-desktop.png'});
});
for(const mode of ['unsupported','denied'])test('fullscreen '+mode+' keeps questionnaire usable and Escape restores normal view',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));await fixture(page,'Customer',true,mode);await page.locator('input[value=D]').check();await expect(page.locator('.assessment-focus-active')).toBeVisible();await page.keyboard.press('Escape');await expect(page.locator('.assessment-focus-active')).toHaveCount(0);await expect(page.locator('input[value=D]')).toBeChecked();await page.locator('input[value=C]').check();await expect(page.locator('.assessment-focus-active')).toHaveCount(0);expect(errors).toEqual([]);
});
test('browser fullscreen exit restores normal view and respects opt out',async({page})=>{
 await fixture(page);await page.locator('input[value=C]').check();await page.evaluate(()=>document.exitFullscreen());await expect(page.locator('.assessment-focus-active')).toHaveCount(0);await page.reload();await expect(page.locator('.assessment-focus-active')).toHaveCount(0);
});
for(const [kind,editable] of [['Auditor',true],['Customer',false]] as const)test(kind+' editable '+editable+' retains normal view',async({page})=>{
 await fixture(page,kind,editable);await expect(page.locator('.assessment-focus-active')).toHaveCount(0);await expect(page.getByRole('button',{name:'Normal view',exact:true})).toHaveCount(0);expect(await page.evaluate(()=>(window as any).requests)).toBe(0);
});
test('mobile focus fits viewport and submission restores surrounding view',async({page})=>{
 await page.setViewportSize({width:390,height:844});await fixture(page);await expect(page.getByRole('button',{name:'Normal view',exact:true})).toBeInViewport();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.locator('input[value=C]').check();await page.getByRole('button',{name:'Next section'}).click();await page.locator('input[value=D]').check();await page.screenshot({path:'test-results/focus-mobile.png'});await page.getByRole('button',{name:'Submit for review'}).click();await expect(page.locator('.assessment-focus-active')).toHaveCount(0);await expect(page.locator('body')).not.toHaveClass(/assessment-focus-mode/);expect(await page.evaluate(()=>document.fullscreenElement===null)).toBe(true);
});

test('real browser fullscreen enters on answering and exits with Normal view',async({page})=>{
 await fixture(page,'Customer',true,'real');test.skip(!await page.evaluate(()=>document.fullscreenEnabled),'Browser does not expose native fullscreen');
 await page.locator('input[value=C]').check();await expect.poll(()=>page.evaluate(()=>document.fullscreenElement?.classList.contains('iam-questionnaire'))).toBe(true);
 await page.getByRole('button',{name:'Normal view',exact:true}).click();await expect.poll(()=>page.evaluate(()=>document.fullscreenElement===null)).toBe(true);await expect(page.locator('.assessment-focus-active')).toHaveCount(0);
 await page.getByRole('button',{name:'Full screen',exact:true}).click();await expect.poll(()=>page.evaluate(()=>!!document.fullscreenElement)).toBe(true);await page.evaluate(()=>document.exitFullscreen());await expect(page.locator('.assessment-focus-active')).toHaveCount(0);
});

test('fullscreen overview and progress hide independently and normal view restores them without losing answers',async({page})=>{
 await fixture(page);await page.locator('input[value=C]').check();
 await page.getByRole('button',{name:'Hide section overview',exact:true}).click();await expect(page.locator('.iam-section-overview')).toHaveCount(0);await expect(page.getByRole('progressbar')).toBeVisible();
 await page.getByRole('button',{name:'Hide progress',exact:true}).click();await expect(page.locator('#assessment-progress-details')).toBeHidden();await expect(page.getByRole('button',{name:'Show progress',exact:true})).toHaveAttribute('aria-expanded','false');
 await page.getByRole('button',{name:'Next section',exact:true}).click();await expect(page.getByText('Question 2',{exact:true})).toBeVisible();await expect(page.locator('#assessment-progress-details')).toBeHidden();await page.getByRole('button',{name:'Previous section',exact:true}).click();await expect(page.locator('input[value=C]')).toBeChecked();
 await page.getByRole('button',{name:'Normal view',exact:true}).click();await expect(page.locator('.iam-section-overview')).toBeVisible();await expect(page.getByRole('progressbar')).toBeVisible();
 await page.getByRole('button',{name:'Full screen',exact:true}).click();await expect(page.locator('.iam-section-overview')).toHaveCount(0);await expect(page.locator('#assessment-progress-details')).toBeHidden();
 await page.getByRole('button',{name:'Show section overview',exact:true}).click();await page.getByRole('button',{name:'Show progress',exact:true}).click();await expect(page.locator('.iam-section-overview')).toBeVisible();await expect(page.getByRole('progressbar')).toBeVisible();await expect(page.locator('input[value=C]')).toBeChecked();
});
for(const normal of [false,true])for(const size of [{width:1440,height:900},{width:320,height:640},{width:740,height:360}])test('long questions and all options scroll in '+(normal?'normal':'fullscreen')+' '+size.width+'x'+size.height,async({page})=>{
 await page.setViewportSize(size);
 if(normal)await page.addInitScript(()=>sessionStorage.setItem('grc-assessment-view:focus%40example.test:FOCUS','normal'));
 await fixture(page,'Customer',true,!normal&&size.width===1440?'real':'unsupported',true);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 const container=page.locator('.assessment-questionnaire-content');
 if(!normal&&size.width===1440){await page.locator('.question-card').first().locator('input[value=A]').check();await expect.poll(()=>page.evaluate(()=>!!document.fullscreenElement)).toBe(true);}
 if(!normal){expect(await container.evaluate(e=>e.scrollHeight>e.clientHeight)).toBe(true);await container.focus();await page.keyboard.press('End');await expect.poll(()=>container.evaluate(e=>e.scrollTop)).toBeGreaterThan(0);}
 await page.locator('.question-card').first().hover();await page.mouse.wheel(0,100000);
 const last=page.locator('.question-card').last();await expect(last).toBeInViewport();
 await last.locator('input[value=D]').check();await expect(last.locator('input[value=D]')).toBeChecked();
 const text=last.locator('.iam-opt-text').nth(3);expect(await text.evaluate(e=>e.scrollHeight<=e.clientHeight+1&&e.scrollWidth<=e.clientWidth+1)).toBe(true);
 await last.locator('input[value="N/A"]').check();await expect(last.locator('input[value="N/A"]')).toBeChecked();
 await page.getByRole('button',{name:'Next section',exact:true}).click();await expect(page.locator('.question-heading h3').first()).toContainText('Question 12');await expect(page.locator('.question-heading h3').first()).toBeInViewport();
 await page.screenshot({path:'test-results/long-questionnaire-'+(normal?'normal':'focus')+'-'+size.width+'.png'});
});
