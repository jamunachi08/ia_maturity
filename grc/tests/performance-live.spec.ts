import {test, expect} from '@playwright/test';
import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {resolve, dirname} from 'node:path';

// Opt-in lab measurements only. All cookies originate from native authentication
// on the separate muted performance site. Never save traces or secret state.
test.skip(process.env.GRC_RUN_PERFORMANCE_LIVE !== '1', 'Requires guarded performance clone and native fixture sessions.');
test.describe.configure({mode:'serial'});
test.use({trace:'off', video:'off', screenshot:'off'});

type Account={email:string;role_key:string;kind:string;home:string;cookies:Record<string,string>};
const bench=resolve('../../..');
const fixture=()=>JSON.parse(readFileSync(resolve(bench,'sites/grc-perf.local/private/performance-fixture.json'),'utf8')) as {users:Record<string,Account>;scale:number};
const profiles=[
  {name:'desktop', viewport:{width:1440,height:1000},latency:20,downloadThroughput:10_000_000,uploadThroughput:5_000_000,cpu:1},
  {name:'mobile',viewport:{width:390,height:844},latency:150,downloadThroughput:500_000,uploadThroughput:125_000,cpu:4},
];
const wanted=(process.env.GRC_PERFORMANCE_ROLES||'anonymous,login,admin,erp,ia_customer,ia_consultant,ia_reviewer,ia_manager,grc_customer,grc_consultant,grc_reviewer,grc_manager').split(',');
const iterations=Number(process.env.GRC_PERFORMANCE_ITERATIONS||'1');
const language=process.env.GRC_PERFORMANCE_LANGUAGE||'en';
if(!['en','ar'].includes(language))throw new Error('Only English and Arabic performance profiles are supported.');
const results:unknown[]=[];

function save(row:unknown){
  const output=resolve(process.env.GRC_PERFORMANCE_BROWSER_OUTPUT||resolve(bench,'diagnostics/performance-20261113/browser.json'));
  if(!output.startsWith(resolve(bench,'diagnostics/performance-20261113')+'/'))throw new Error('Only local sanitized performance evidence output is allowed.');
  mkdirSync(dirname(output),{recursive:true});results.push(row);
  writeFileSync(output,JSON.stringify({environment:'local synthetic Chromium lab; interaction samples are not field INP',language,
    portal_readiness_method:'browser_native_complete_first_page_stable_layout_v1',
    font_settlement_method:'stylesheet_terminal_event_then_FontFaceSet_ready',
    fixture_scope:'nonempty authorized first page with Organization and Status selectors',expected_groups:profiles.length*wanted.length,results},null,2));
}

for(const profile of profiles)for(const role of wanted)test(`${profile.name}: ${role} cold/warm load and ready time`,async({browser,baseURL})=>{
  test.setTimeout(Math.max(180000,iterations*60000));
  const target=new URL(baseURL||'');
  expect(target.hostname).toBe('127.0.0.1');expect(['8011','8012','8013','8014']).toContain(target.port);
  const state=fixture(),account=state.users[role];
  const context=await browser.newContext({baseURL,viewport:profile.viewport});
  try{
    if(account)await context.addCookies(Object.entries(account.cookies).map(([name,value])=>({name,value,domain:'127.0.0.1',path:'/'})));
    await context.addInitScript(({email,language,portal})=>{
      if(location.hostname!=='127.0.0.1')return;
      localStorage.setItem('grc-language',language);
      if(email)localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(email)+':skip-auto','1');
      const interactions=new Set<number>();
      (window as any).__perf={lcp:0,cls:0,long_tasks:[],interaction_sample_max:null,interaction_count:0,
        font_stylesheet_events:[],event_timing_supported:PerformanceObserver.supportedEntryTypes.includes('event')};
      (window as any).__fontCssOutcomes={};
      for(const outcome of ['load','error'])document.addEventListener(outcome,event=>{
        const link=event.target;
        if(!(link instanceof HTMLLinkElement)||new URL(link.href).hostname!=='fonts.googleapis.com'||!(link.as==='style'||link.rel==='stylesheet'))return;
        const loaded=link.rel==='stylesheet'&&!!link.sheet;
        if(outcome==='error'||loaded)(window as any).__fontCssOutcomes[link.href]=outcome==='error'?'error':'loaded';
        (window as any).__perf.font_stylesheet_events.push({outcome,at_ms:performance.now(),rel:link.rel,sheet_registered:!!link.sheet});
      },true);
      try{new PerformanceObserver(list=>{for(const e of list.getEntries() as any){
        (window as any).__perf.lcp=e.startTime;
        (window as any).__perf.lcp_element_tag=e.element?.tagName||null;
      }}).observe({type:'largest-contentful-paint',buffered:true})}catch{}
      try{new PerformanceObserver(list=>{for(const e of list.getEntries() as any)if(!e.hadRecentInput)(window as any).__perf.cls+=e.value}).observe({type:'layout-shift',buffered:true})}catch{}
      try{new PerformanceObserver(list=>{for(const e of list.getEntries())(window as any).__perf.long_tasks.push({start_ms:e.startTime,duration_ms:e.duration})}).observe({type:'longtask',buffered:true})}catch{}
      try{new PerformanceObserver(list=>{for(const e of list.getEntries() as any)if(e.interactionId){interactions.add(e.interactionId);(window as any).__perf.interaction_count=interactions.size;(window as any).__perf.interaction_sample_max=Math.max((window as any).__perf.interaction_sample_max||0,e.duration)}}).observe({type:'event',durationThreshold:16,buffered:true} as any)}catch{}
      const laidOut=(node:Element|null)=>{
        if(!node)return false;
        const rect=node.getBoundingClientRect(),style=getComputedStyle(node);
        return rect.width>0&&rect.height>0&&style.display!=='none'&&style.visibility!=='hidden'
          &&node.checkVisibility({checkOpacity:false,checkVisibilityCSS:true})
          &&!node.closest('[hidden],[inert]');
      };
      const visible=(node:Element|null)=>laidOut(node)&&node!.checkVisibility({checkOpacity:true,checkVisibilityCSS:true});
      const interactive=(node:Element|null)=>visible(node)&&getComputedStyle(node!).pointerEvents!=='none'
        &&!node!.matches(':disabled')&&node!.getAttribute('aria-disabled')!=='true';
      (window as any).__observePortalReady=(key:string,cardsRequired:boolean,expectedPath:string,startedAt:number)=>{
        let previous='',stable=0;
        const frame=()=>{
          const main=document.querySelector('.main-content');
          const cards=[...document.querySelectorAll('.main-content .stat-card')];
          const records=main?[...main.querySelectorAll('tbody .record-link')]:[];
          const search=main?.querySelector('.toolbar .search-input input')||null;
          const pagination=main?.querySelector('.pagination')||null;
          const selects=main?[...main.querySelectorAll('.toolbar .grc-select')]:[];
          const controls=main?[...main.querySelectorAll('.toolbar input,.toolbar button,.toolbar select,.toolbar [role="combobox"]')].filter(node=>!node.matches('.grc-select-native')&&visible(node)):[];
          const loading=[...document.querySelectorAll('.loading,.skeleton,[aria-busy="true"]')].some(visible);
          const overlay=[...document.querySelectorAll('[role="dialog"],[aria-modal="true"],.modal-backdrop,.page-tour-backdrop,.sidebar-scrim')]
            .some(node=>visible(node)||laidOut(node)&&getComputedStyle(node).pointerEvents!=='none');
          const blocked=loading||overlay;
          const cardsReady=cardsRequired?cards.length===4&&cards.every(card=>interactive(card)&&/^[\p{Nd}]+(?:[,٬][\p{Nd}]{3})*$/u.test(card.querySelector('strong')?.textContent?.trim()||'')):cards.length===0;
          const destinationReady=location.pathname===expectedPath&&(cardsRequired||main?.querySelector('.page-title h1')?.textContent?.trim()===(language==='ar'?'التقييمات':'Assessments'));
          const enabled=interactive(search)&&!search!.hasAttribute('readonly')&&selects.length===2
            &&selects.every(select=>interactive(select.querySelector('.grc-select-trigger[role="combobox"]')))&&controls.every(interactive);
          const total=Number(pagination?.querySelector('.muted')?.textContent?.match(/\d+/)?.[0]??NaN);
          const expectedRows=Math.min(15,total),columnCount=main?.querySelectorAll('thead th').length||0;
          const firstPageReady=expectedRows>0&&records.length===expectedRows&&records.every(record=>{
            const cells=record.closest('tr')?.querySelectorAll('td');
            return interactive(record)&&!!record.textContent?.trim()&&cells?.length===columnCount&&columnCount>0
              &&[...cells].every(cell=>visible(cell)&&cell.childNodes.length>0);
          })&&visible(pagination);
          if(destinationReady&&cardsReady&&firstPageReady&&enabled&&!blocked){
            const signature=[...cards,...records,...controls,search!,pagination!].map(node=>{const rect=node.getBoundingClientRect();return [rect.x,rect.y,rect.width,rect.height].map(v=>Math.round(v*4)/4).join(',')}).join(';');
            stable=signature===previous?stable+1:1;previous=signature;
            if(stable>=3){
              (window as any).__perf[key]=performance.now()-startedAt;
              (window as any).__perf[key+'_proof']={cards:cards.length,first_page_rows:records.length,expected_first_page_rows:expectedRows,complete_columns:columnCount,pagination_laid_out:true,search_enabled:true,enabled_selects:selects.length,enabled_visible_toolbar_controls:controls.length,stable_frames:stable,blocking_overlay:false};
              return;
            }
          }else{stable=0;previous=''}
          requestAnimationFrame(frame);
        };
        requestAnimationFrame(frame);
      };
      if(portal)(window as any).__observePortalReady('portal_ready_ms',true,location.pathname,0);
      if(!email&&location.pathname==='/login'){
        const heading=language==='ar'?'مرحباً بعودتك':'Welcome back';
        const observeHeading=()=>{
          const element=[...document.querySelectorAll('h1,h2,h3')].find(e=>e.textContent?.trim()===heading);
          if(element&&element.getBoundingClientRect().width&&getComputedStyle(element).visibility!=='hidden'){
            requestAnimationFrame(()=>(window as any).__perf.login_heading_paint_ms=performance.now());
          }else requestAnimationFrame(observeHeading);
        };
        requestAnimationFrame(observeHeading);
      }
    },{email:account?.email||'',language,portal:!!account&&account.kind!=='ERP'});
    const page=await context.newPage(),cdp=await context.newCDPSession(page);
    await cdp.send('Network.enable');await cdp.send('Emulation.setCPUThrottlingRate',{rate:profile.cpu});
    await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:profile.latency,downloadThroughput:profile.downloadThroughput,uploadThroughput:profile.uploadThroughput});
    for(let iteration=1;iteration<=iterations;iteration++)for(const temperature of ['cold','warm']){
      await cdp.send('Network.setCacheDisabled',{cacheDisabled:temperature==='cold'});
      if(temperature==='cold')await cdp.send('Network.clearBrowserCache');
      const failed:string[]=[];
      const failure=(request:any)=>failed.push(new URL(request.url()).hostname);
      page.on('requestfailed',failure);
      const start=Date.now();
      await page.goto(account?account.home:role==='login'?'/login':'/grc-site',{waitUntil:'domcontentloaded',timeout:150000});
      if(account?.kind==='ERP')await expect(page.locator('.layout-main-section').first().or(page.getByText('Setup your organization',{exact:true})).first()).toBeVisible({timeout:120000});
      else if(account){
        await expect(page.locator('.stat-card').first()).toBeVisible({timeout:120000});
        await expect(page.locator('.record-link').first()).toBeVisible({timeout:120000});
        await expect(page.locator('.main-content .loading')).toHaveCount(0);
        await page.waitForFunction(()=>(window as any).__perf.portal_ready_ms>0,undefined,{timeout:120000});
      }else if(role==='login')await expect(page.getByRole('heading',{name:language==='ar'?'مرحباً بعودتك':'Welcome back',exact:true})).toBeVisible({timeout:120000});
      else await expect(page.locator('.public-site')).toBeVisible({timeout:120000});
      const driverReady=Date.now()-start;
      const ready=account&&account.kind!=='ERP'?await page.evaluate(()=>(window as any).__perf.portal_ready_ms):driverReady;
      if(account?.kind!=='ERP')await expect(page.locator('html')).toHaveAttribute('dir',language==='ar'?'rtl':'ltr');
      await page.waitForFunction(()=>[...document.querySelectorAll<HTMLLinkElement>('link')]
        .filter(link=>new URL(link.href).hostname==='fonts.googleapis.com'&&(link.as==='style'||link.rel==='stylesheet'))
        .every(link=>(window as any).__fontCssOutcomes[link.href]==='error'
          ||link.rel==='stylesheet'&&!!link.sheet&&(window as any).__fontCssOutcomes[link.href]==='loaded'),undefined,{timeout:30000});
      await page.evaluate(async()=>{
        await document.fonts.ready;
        (window as any).__perf.font_settlement={settled_at_ms:performance.now(),fonts_status:document.fonts.status,
          links:[...document.querySelectorAll<HTMLLinkElement>('link')]
            .filter(link=>new URL(link.href).hostname==='fonts.googleapis.com'&&(link.as==='style'||link.rel==='stylesheet'))
            .map(link=>({host:new URL(link.href).hostname,path:new URL(link.href).pathname,rel:link.rel,
              sheet_registered:!!link.sheet,outcome:(window as any).__fontCssOutcomes[link.href],
              resource_timing_present:performance.getEntriesByName(link.href,'resource').length>0}))};
      });
      await page.evaluate(()=>new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve()))));
      await page.waitForTimeout(100);
      const metrics=await page.evaluate(()=>({...(window as any).__perf,
        navigation:(performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming)?.toJSON(),
        resources:performance.getEntriesByType('resource').map(e=>{const r=e as PerformanceResourceTiming;return {path:new URL(r.name).pathname,host:new URL(r.name).hostname,type:r.initiatorType,start_ms:r.startTime,response_end_ms:r.responseEnd,duration:r.duration,transfer_bytes:r.transferSize,encoded_bytes:r.encodedBodySize}})}));
      let navigationMs:number|undefined;
      let driverNavigationMs:number|undefined;
      if(account&&account.kind!=='ERP'){
        if(profile.name==='mobile')await page.getByRole('button',{name:language==='ar'?'القائمة':'Menu',exact:true}).click();
        await page.evaluate(expected=>{
          const begin=(event:MouseEvent)=>{
            const link=(event.target as Element)?.closest('a');
            if(!link||new URL(link.href).pathname!==expected)return;
            document.removeEventListener('click',begin,true);
            (window as any).__perf.navigation_ready_ms=null;
            (window as any).__observePortalReady('navigation_ready_ms',false,expected,event.timeStamp);
          };
          document.addEventListener('click',begin,true);
        },account.home+'/assessments');
        const navigationStart=Date.now();
        await page.getByRole('link',{name:language==='ar'?'التقييمات':'Assessments',exact:true}).first().click();
        await expect(page).toHaveURL(/\/assessments$/);
        await expect(page.locator('.record-link').first()).toBeVisible();
        await expect(page.locator('.main-content .loading')).toHaveCount(0);
        await page.waitForFunction(()=>(window as any).__perf.navigation_ready_ms>0,undefined,{timeout:120000});
        driverNavigationMs=Date.now()-navigationStart;
        navigationMs=await page.evaluate(()=>(window as any).__perf.navigation_ready_ms);
      }
      if(!account){
        await page.getByRole('button',{name:language==='ar'?'English':'العربية',exact:true}).click();
        await expect(page.locator('html')).toHaveAttribute('dir',language==='ar'?'ltr':'rtl');
      }
      await page.evaluate(()=>new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve()))));
      const interaction=await page.evaluate(()=>({max:(window as any).__perf.interaction_sample_max,
        count:(window as any).__perf.interaction_count,supported:(window as any).__perf.event_timing_supported,
        navigation_ready_proof:(window as any).__perf.navigation_ready_ms_proof}));
      metrics.interaction_sample_max=interaction.max;
      metrics.interaction_count=interaction.count;
      metrics.navigation_ready_proof=interaction.navigation_ready_proof;
      metrics.interaction_measurement_status=account?.kind==='ERP'?'not_sampled_native_setup':!interaction.supported?'unsupported':interaction.count?'observed':'no_event_at_16ms_threshold';
      save({base_url:baseURL,role,profile:profile.name,language,temperature,iteration,scale:state.scale,ready_ms:ready,
        driver_ready_ms:driverReady,ready_clock:account&&account.kind!=='ERP'?'browser_native_stable_layout':'driver_diagnostic',
        internal_navigation_ms:navigationMs,driver_navigation_ms:driverNavigationMs,metrics,failed_resource_hosts:[...new Set(failed)],
        conditions:{latency_ms:profile.latency,download_bytes_per_second:profile.downloadThroughput,cpu_slowdown:profile.cpu}});
      page.off('requestfailed',failure);
    }
  }finally{await context.close()}
});

test.afterAll(()=>{
  if(process.env.GRC_PERFORMANCE_ASSERT_BUDGETS!=='1')return;
  const percentile=(values:number[],p:number)=>values.sort((a,b)=>a-b)[Math.ceil(values.length*p)-1];
  for(const profile of profiles)for(const role of wanted){
    const rows=(results as any[]).filter(r=>r.profile===profile.name&&r.role===role);
    expect(rows.length,`${profile.name}/${role}: percentile gates require >=20 observations`).toBeGreaterThanOrEqual(20);
    if(role!=='erp')expect(rows.every(r=>r.metrics.font_settlement?.links.length===1),`${profile.name}/${role}: expected active font stylesheet`).toBe(true);
    expect(rows.every(r=>r.metrics.font_settlement?.fonts_status==='loaded'
      &&r.metrics.font_settlement.links.every((link:any)=>link.outcome==='loaded'&&link.sheet_registered)),`${profile.name}/${role}: stylesheet and font settlement proof`).toBe(true);
    if(['anonymous','login'].includes(role)){
      expect(rows.every(r=>r.metrics.lcp>0),`${profile.name}/${role}: LCP observation must be available`).toBe(true);
      expect(percentile(rows.map(r=>r.metrics.lcp),.75),`${profile.name}/${role}: p75 LCP`).toBeLessThanOrEqual(2500);
    }
    if(!['anonymous','login','erp'].includes(role)){
      expect(rows.every(r=>r.ready_clock==='browser_native_stable_layout'),`${profile.name}/${role}: browser-native ready clock`).toBe(true);
      expect(rows.every(r=>r.metrics.portal_ready_ms_proof?.cards===4&&r.metrics.portal_ready_ms_proof?.stable_frames>=3),`${profile.name}/${role}: dashboard readiness proof`).toBe(true);
      expect(rows.every(r=>r.metrics.navigation_ready_proof?.cards===0&&r.metrics.navigation_ready_proof?.stable_frames>=3),`${profile.name}/${role}: destination navigation proof`).toBe(true);
      expect(percentile(rows.map(r=>r.ready_ms),.95),`${profile.name}/${role}: p95 dashboard ready`).toBeLessThanOrEqual(3000);
      expect(percentile(rows.map(r=>r.internal_navigation_ms),.95),`${profile.name}/${role}: p95 navigation`).toBeLessThanOrEqual(1000);
    }
    expect(percentile(rows.map(r=>r.metrics.cls),.75),`${profile.name}/${role}: p75 CLS`).toBeLessThanOrEqual(.1);
  }
});
