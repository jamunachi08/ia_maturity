frappe.pages["grc-staff"].on_page_load = function(wrapper) {
 const page=frappe.ui.make_app_page({parent:wrapper,title:__("GRC Staff"),single_column:true});

 const call=(method,args={})=>frappe.xcall("ia_maturity.grc.api."+method,args);
 const body=$(wrapper).find(".layout-main-section");
 if(frappe.session.user==='Administrator'||frappe.user_roles.includes('GRC App Admin')||frappe.user_roles.includes('GRC Manager')){
  call('maturity_display_settings').then(data=>{
   const card=$('<section class="border rounded p-3 mb-4"></section>').prependTo(body);
   $('<h3></h3>').text(__('Assessment display')).appendTo(card);
   const control=frappe.ui.form.make_control({parent:card,df:{fieldname:'overall_maturity_visibility',label:__('Overall Maturity panel'),fieldtype:'Select',options:data.options.join('\n')},render_input:true});
   control.set_value(data.mode);let expected=data.mode;
   $('<p></p>').text(__('Hidden removes the entire panel. Completed sections only shows scores for fully answered sections without an overall score.')).appendTo(card);
   const save=$('<button class="btn btn-primary"></button>').text(__('Save display setting')).appendTo(card);
   save.on('click',async()=>{save.prop('disabled',true);try{const result=await call('save_maturity_display',{mode:control.get_value(),expected_mode:expected});expected=result.mode;frappe.show_alert({message:__('Display setting saved.'),indicator:'green'})}catch(error){frappe.msgprint(error.message||__('Could not save display setting.'))}finally{save.prop('disabled',false)}});
  }).catch(frappe.msgprint);
 }
 page.set_primary_action(__("Open staff workspace"),()=>location.assign("/grc/auditor"));
 $('<label></label>').text(__("Organization")).appendTo(body);
 const org=$('<select class="form-control" aria-label="Organization"></select>').appendTo(body);
 $('<label class="mt-3"></label>').text(__("Assessment")).appendTo(body);
 const assessment=$('<select class="form-control mt-3" aria-label="Assessment"></select>').appendTo(body);
 const panel=$('<div class="mt-4"></div>').appendTo(body);
 let rows=[],generation=0;
 async function show(){
  const current=++generation;
  const row=rows.find(a=>a.grc_assignment===assessment.val());
  const activities=await call("activity",{entity:org.val(),assignment:row?.grc_assignment});
  if(current!==generation)return;
  panel.empty();
  if(row)$('<a class="btn btn-default mb-3"></a>').text(__("Open assessment")).attr("href","/grc/auditor/assessments/"+encodeURIComponent(row.name)).appendTo(panel);
  $('<h3></h3>').text(__("Detailed assessment activity")).appendTo(panel);
  let offset=0;
  const controls=$('<div class="mb-3"></div>').appendTo(panel);
  const list=$('<div></div>').appendTo(panel);
  function render(){
   controls.empty();list.empty();
   const previous=$('<button class="btn btn-default mr-2"></button>').text(__("Previous")).prop("disabled",offset===0).appendTo(controls);
   const next=$('<button class="btn btn-default mr-2"></button>').text(__("Next")).prop("disabled",offset+25>=activities.length).appendTo(controls);
   $('<span></span>').text((offset+1)+"–"+Math.min(offset+25,activities.length)+" / "+activities.length).appendTo(controls);
   previous.on("click",()=>{offset=Math.max(0,offset-25);render()});
   next.on("click",()=>{offset+=25;render()});
   for(const a of activities.slice(offset,offset+25)){
   const item=$('<article class="border rounded p-3 mb-3"></article>').appendTo(list);
   $('<strong></strong>').text(__(a.action)).appendTo(item);
   $('<p></p>').text(a.actor+" · "+a.creation).appendTo(item);
   const details=$('<details></details>').appendTo(item);
   $('<summary></summary>').text(__("Details")).appendTo(details);
   $('<pre style="white-space:pre-wrap"></pre>').text(JSON.stringify(JSON.parse(a.details||"{}"),null,2)).appendTo(details);
  }
   }
  if(activities.length)render();
  if(!activities.length)$('<p></p>').text(__("No activity yet.")).appendTo(panel);
 }
 async function load(){
  const data=await call("dashboard",{entity:org.val()});
  rows=data.assessments;
  assessment.empty().append($('<option value=""></option>').text(__("All assessment activity")));
  rows.forEach(a=>$('<option></option>').val(a.grc_assignment).text(a.name+" · "+__(a.state)).appendTo(assessment));
  await show();
 }
 org.on("change",()=>load().catch(frappe.msgprint));
 assessment.on("change",()=>show().catch(frappe.msgprint));
 call("organizations").then(data=>{
  org.empty();
  data.forEach(o=>$('<option></option>').val(o.name).text(o.entity_name).appendTo(org));
  if(data.length)return load();
  panel.text(__("No customers assigned."));
 }).catch(frappe.msgprint);
};
