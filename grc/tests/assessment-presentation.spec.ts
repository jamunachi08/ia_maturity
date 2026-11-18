import {test,expect} from '@playwright/test';
test.beforeEach(async({page})=>{await page.addInitScript(()=>sessionStorage.setItem('grc-assessment-view:qa%40example.test:QA','normal'))});
for(const expanded of [false,true])test('assessment disclosures and extras '+expanded,async({page})=>{
 const objects=['<</Type/Catalog/Pages 2 0 R>>','<</Type/Pages/Kids[3 0 R]/Count 1>>','<</Type/Page/Parent 2 0 R/MediaBox[0 0 792 612]/Resources<<>>>>'];
 let pdf='%PDF-1.4\n';const offsets=[0];for(const [i,obj] of objects.entries()){offsets.push(pdf.length);pdf+=(i+1)+' 0 obj\n'+obj+'\nendobj\n'}const xref=pdf.length;pdf+='xref\n0 4\n0000000000 65535 f \n'+offsets.slice(1).map(n=>String(n).padStart(10,'0')+' 00000 n \n').join('')+'trailer\n<</Size 4/Root 1 0 R>>\nstartxref\n'+xref+'\n%%EOF';
 await page.route('**/api/method/ia_maturity.grc.api.download_report?**',r=>r.fulfill({contentType:'application/pdf',body:pdf}));
 const user='qa@example.test';await page.addInitScript(()=>localStorage.setItem('grc-language','en'));
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind:'Customer',user,home:'/grc/customer',organizations:[],workspace_preferences:{show_page_tour:false,show_help:false}}}}));
 await page.route('**/api/method/ia_maturity.grc.api.assessment?**',r=>r.fulfill({json:{message:{name:'QA',entity:'QA organization',template:'QA',modified:'v1',docstatus:0,editable:true,results_visible:true,released:false,review_actions:[],overall_maturity_visibility:'After assessment completion',customer_score_timing:'During assessment',can_download_report:true,pdf_url:'/api/method/ia_maturity.grc.api.download_report?name=QA',expand_maturity:expanded,expand_report:expanded,overall_score:75,maturity_level:'High',questions:[{question_code:'Q1',section_code:'S1',section_title:'Governance',question_text:'Is governance established?',option_a:'Ad hoc',option_b:'Basic',option_c:'Established',option_d:'Leading',selected_option:'C',allow_comment:expanded?1:0,allow_attachment:expanded?1:0}]}}}));
 await page.route('**/api/method/ia_maturity.grc.api.activity**',r=>r.fulfill({json:{message:[]}}));
 await page.goto('/grc/customer/assessments/QA');
 const maturity=page.locator('.maturity-disclosure'),report=page.locator('.report-disclosure');
 await expect(maturity).toBeVisible();await expect(report).toBeVisible();
 expect(await maturity.evaluate(e=>(e as HTMLDetailsElement).open)).toBe(true);
 expect(await report.evaluate(e=>(e as HTMLDetailsElement).open)).toBe(expanded);
 await maturity.locator('summary').click();expect(await maturity.evaluate(e=>(e as HTMLDetailsElement).open)).toBe(false);
 await expect(page.getByText('Comment (optional)',{exact:true})).toHaveCount(expanded?1:0);
 await expect(page.getByText('Attach evidence',{exact:true})).toHaveCount(expanded?1:0);
 if(!expanded)await report.locator('summary').click();
 await expect(report.locator('iframe[title="Report preview"]')).toBeVisible();
 await expect(report.locator('iframe')).toHaveAttribute('src','/api/method/ia_maturity.grc.api.download_report?name=QA&inline=1');
 await expect(report.getByRole('link',{name:'Download PDF',exact:true})).toHaveAttribute('href','/api/method/ia_maturity.grc.api.download_report?name=QA');
 await page.setViewportSize({width:390,height:844});await expect(page.getByText('Is governance established?')).toBeVisible();
 await page.screenshot({path:'test-results/assessment-'+expanded+'.png',fullPage:true});
});

for(const mode of ['default','during','hidden','submitted'])test('customer visibility '+mode,async({page})=>{
 const doc:any={name:'QA',entity:'QA organization',template:'QA',modified:'v1',docstatus:0,editable:true,results_visible:true,released:false,review_actions:[],overall_maturity_visibility:'After assessment completion',overall_score:75,maturity_level:'High',scoring:{points:{A:25,B:50,C:75,D:100},max_points:100,bands:[{level_name:'Medium',min_score:0,color:'#9A6F00'}]},questions:[{question_code:'Q1',section_code:'S1',section_title:'Governance',question_text:'Is governance established?',option_a:'Ad hoc',option_b:'Basic',option_c:'Established',option_d:'Leading',allow_comment:0,allow_attachment:0}]};
 if(mode==='during'){doc.customer_score_timing='During assessment';doc.customer_sections_visibility='Always expanded'}
 if(mode==='hidden')doc.customer_sections_visibility='Hidden';
 if(mode==='submitted')doc.customer_score_timing='After submission';
 await page.addInitScript(()=>localStorage.setItem('grc-language','en'));
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind:'Customer',user:'qa@example.test',home:'/grc/customer',organizations:[],workspace_preferences:{show_page_tour:false,show_help:false}}}}));
 await page.route('**/api/method/ia_maturity.grc.api.assessment?**',r=>r.fulfill({json:{message:doc}}));
 await page.route('**/api/method/ia_maturity.grc.api.save_assessment',r=>{const body=r.request().postDataJSON();doc.questions[0].selected_option=body.answers.Q1.selected_option;return r.fulfill({json:{message:doc}})});
 await page.route('**/api/method/ia_maturity.grc.api.activity**',r=>r.fulfill({json:{message:[]}}));
 await page.goto('/grc/customer/assessments/QA');
 const overview=page.locator('.iam-section-overview');
 if(mode==='hidden')await expect(overview).toHaveCount(0);else{await expect(overview).toBeVisible();expect(await overview.evaluate(e=>(e as HTMLDetailsElement).open)).toBe(mode!=='hidden')}
 await expect(page.locator('.iam-live-score')).toHaveCount(0);
 await expect(page.locator('.maturity-disclosure')).toHaveCount(0);
 await expect(page.locator('.maturity-disclosure .score-value')).toHaveCount(0);
 await expect(page.locator('.assessment-progress')).toContainText('1 pending');
 await expect(page.getByText('Comment (optional)',{exact:true})).toHaveCount(0);await expect(page.getByText('Attach evidence',{exact:true})).toHaveCount(0);
 await page.locator('input[type=radio][value=C]').check();
 await expect(page.locator('.assessment-progress')).toContainText('0 pending');
 await expect(page.locator('.iam-live-score')).toHaveCount(mode==='submitted'?0:1);
 if(mode==='default')expect(await overview.evaluate(e=>(e as HTMLDetailsElement).open)).toBe(true);
 await page.setViewportSize({width:390,height:844});await expect(page.getByText('Is governance established?')).toBeVisible();
 await page.screenshot({path:'test-results/customer-visibility-'+mode+'.png',fullPage:true});
});

test('opening view shows six section tabs, compact disclosure actions and rounded progress',async({page})=>{
 const questions=Array.from({length:6},(_,i)=>({question_code:'Q'+(i+1),section_code:'S'+(i+1),section_title:['Governance, Independence & Ethics','Risk-Based Audit Planning','Audit Execution, Methodology & Analytics','Reporting, Issue Management & Follow-up','Resources, Performance & Quality Assurance','Strategic Value, Technology & Regulatory Compliance'][i],question_text:'How is domain '+(i+1)+' governed?',option_a:'Ad hoc',option_b:'Foundational',option_c:'Established',option_d:'Leading',allow_comment:0,allow_attachment:0}));
 await page.addInitScript(()=>localStorage.setItem('grc-language','en'));
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind:'Customer',user:'qa@example.test',home:'/grc/customer',organizations:[],workspace_preferences:{show_page_tour:false,show_help:false}}}}));
 await page.route('**/api/method/ia_maturity.grc.api.assessment?**',r=>r.fulfill({json:{message:{name:'QA',entity:'Example organization',template:'Default questionnaire',docstatus:0,editable:true,results_visible:false,released:false,review_actions:[],questions}}}));
 await page.route('**/api/method/ia_maturity.grc.api.activity**',r=>r.fulfill({json:{message:[]}}));
 await page.goto('/grc/customer/assessments/QA');
 await expect(page.getByRole('heading',{name:'Internal Audit Maturity Assessment',exact:true})).toBeVisible();
 await expect(page.locator('.iam-stepper button')).toHaveCount(6);
 await expect(page.locator('.iam-stepper button').last()).toBeVisible();
 await expect(page.locator('.maturity-disclosure')).toHaveCount(0);
 await expect(page.locator('.report-disclosure summary')).toContainText('Available after report release');
 await page.locator('.report-disclosure summary').focus();await page.keyboard.press('Enter');
 await expect(page.locator('.report-disclosure summary .when-open')).toBeVisible();
 await page.locator('.report-disclosure summary').click();
 await expect(page.getByRole('progressbar',{name:'Assessment progress'})).toHaveAttribute('aria-valuenow','0');
 expect(await page.getByRole('progressbar').evaluate(e=>getComputedStyle(e).borderRadius)).toBe('999px');
 await page.getByRole('heading',{name:'Internal Audit Maturity Assessment',exact:true}).click();
 await page.screenshot({path:'test-results/questionnaire-opening-desktop.png',fullPage:true,animations:'disabled'});
 await page.setViewportSize({width:390,height:844});await expect(page.locator('.iam-stepper button').last()).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await expect.poll(()=>page.locator('.sidebar').evaluate(e=>Math.ceil(e.getBoundingClientRect().right))).toBeLessThanOrEqual(0);
 await page.screenshot({path:'test-results/questionnaire-opening-mobile.png',fullPage:true,animations:'disabled'});
});
test('frontend section bars use the shared percentage palette independently of maturity labels',async({page})=>{
 const values=[100,99.9,75,74.9,50,49.9];
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind:'Auditor',user:'qa@example.test',home:'/grc/auditor',organizations:[],workspace_preferences:{show_page_tour:false,show_help:false}}}}));
 await page.route('**/api/method/ia_maturity.grc.api.assessment?**',r=>r.fulfill({json:{message:{name:'QA',entity:'Example',template:'Default',docstatus:1,editable:false,results_visible:true,released:false,review_actions:[],expand_maturity:true,overall_maturity_visibility:'After assessment completion',questions:values.map((_,i)=>({question_code:'Q'+i,section_code:'S'+i,selected_option:'C'})),section_scores:values.map((score_pct,i)=>({section_code:'S'+i,section_title:'Domain '+i,score_pct,maturity_level:'Medium'}))}}}));
 await page.route('**/api/method/ia_maturity.grc.api.activity**',r=>r.fulfill({json:{message:[]}}));
 await page.goto('/grc/auditor/assessments/QA');
 const expected=['rgb(28, 92, 163)','rgb(45, 122, 51)','rgb(45, 122, 51)','rgb(191, 83, 11)','rgb(191, 83, 11)','rgb(180, 35, 24)'];
 for(let i=0;i<values.length;i++)await expect(page.locator('.score-row .progress-track span').nth(i)).toHaveCSS('background-color',expected[i]);
});
