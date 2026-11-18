import {test,expect} from '@playwright/test';
import {sectionScoreColor} from '../src/sectionScoreColor';
for(const role of ['admin','manager'])test(role+' can build and save ten ranges',async({page})=>{
 let config:any={ranges:[{min_score:0,color:'#B42318'},{min_score:50,color:'#BF530B'},{min_score:75,color:'#2D7A33'},{min_score:100,color:'#1C5CA3'}],revision:'old'};let saved:any;
 await page.addInitScript(()=>localStorage.setItem('grc-language','en'));
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind:'Auditor',is_admin:role==='admin',staff_roles:role==='manager'?['GRC Manager']:['GRC App Admin'],user:'qa@example.test',home:'/grc/auditor',organizations:[],workspace_preferences:{show_page_tour:false,show_help:false}}}}));
 await page.route('**/api/method/ia_maturity.grc.api.color_ranges',r=>r.fulfill({json:{message:config}}));
 await page.route('**/api/method/ia_maturity.grc.api.save_color_ranges',r=>{saved=r.request().postDataJSON();config={ranges:saved.ranges,revision:'new'};return r.fulfill({json:{message:config}})});
 await page.goto('/grc/auditor');await page.getByRole('link',{name:'Report color ranges',exact:true}).click();
 for(let i=0;i<6;i++)await page.getByRole('button',{name:'Add range',exact:true}).click();
 await expect(page.getByLabel(/^Range start /)).toHaveCount(10);
 await page.getByLabel('Hex color 1',{exact:true}).fill('#123456');
 await page.getByRole('button',{name:'Save color ranges',exact:true}).click();
 await expect(page.getByRole('status')).toHaveText('Color ranges saved.');expect(saved.ranges).toHaveLength(10);expect(saved.expected_revision).toBe('old');
 expect(sectionScoreColor(0,saved.ranges)).toBe('#123456');
 await page.reload();await expect(page.getByLabel(/^Range start /)).toHaveCount(10);await expect(page.getByLabel('Hex color 1',{exact:true})).toHaveValue('#123456');
 if(role==='manager')await page.screenshot({path:'test-results/manager-ten-color-ranges.png',fullPage:true,animations:'disabled'});
 await page.setViewportSize({width:390,height:844});await expect(page.getByRole('button',{name:'Add range',exact:true})).toBeVisible();
});
test('ten range frontend lookup uses the same inclusive lower bounds as PDF policy',()=>{
 const ranges=Array.from({length:10},(_,i)=>({min_score:i*10,color:'#'+String(i).repeat(6)}));
 for(let i=0;i<10;i++){expect(sectionScoreColor(i*10,ranges)).toBe(ranges[i].color);expect(sectionScoreColor(i*10+9.99,ranges)).toBe(ranges[i].color)}
 expect(sectionScoreColor(100,ranges)).toBe(ranges[9].color);
});

test('custom ten-range policy colors actual assessment bars',async({page})=>{
 const ranges=Array.from({length:10},(_,i)=>({min_score:i*10,color:'#'+String(i).repeat(6)}));
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',r=>r.fulfill({json:{message:{enabled:true,kind:'Auditor',user:'qa@example.test',home:'/grc/auditor',organizations:[],workspace_preferences:{show_page_tour:false,show_help:false}}}}));
 await page.route('**/api/method/ia_maturity.grc.api.assessment?**',r=>r.fulfill({json:{message:{name:'QA',entity:'Example',template:'Default',docstatus:1,editable:false,results_visible:true,released:false,review_actions:[],expand_maturity:true,overall_maturity_visibility:'After assessment completion',questions:ranges.map((_,i)=>({question_code:'Q'+i,section_code:'S'+i,selected_option:'C'})),section_color_ranges:ranges,section_scores:ranges.map((_,i)=>({section_code:'S'+i,section_title:'Domain '+i,score_pct:i*10+5,maturity_level:'Medium'}))}}}));
 await page.route('**/api/method/ia_maturity.grc.api.activity**',r=>r.fulfill({json:{message:[]}}));
 await page.goto('/grc/auditor/assessments/QA');
 for(let i=0;i<10;i++)await expect(page.locator('.score-row .progress-track span').nth(i)).toHaveCSS('background-color','rgb('+[i*17,i*17,i*17].join(', ')+')');
});
