import ts from 'typescript';import fs from 'node:fs';
const catalogue=JSON.parse(fs.readFileSync('src/site-content-defaults.json','utf8'));
function key(en,ar){let h=2166136261;for(const c of en+'\0'+ar){h^=c.codePointAt(0);h=Math.imul(h,16777619)}return 's'+(h>>>0).toString(16).padStart(8,'0')}
let failures=0,checked=0;
function check(en,ar,source){if(typeof en!=='string'||typeof ar!=='string')return;checked++;const item=catalogue[key(en,ar)];if(!item||item.en!==en||item.ar!==ar){console.error('Missing or mismatched catalogue entry:',source,en);failures++}}
for(const file of ['src/pages/Public.tsx','src/pages/LandingHome.tsx']){
 const sf=ts.createSourceFile(file,fs.readFileSync(file,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 function value(node){if(ts.isStringLiteral(node))return node.text;if(ts.isArrayLiteralExpression(node))return node.elements.map(value);if(ts.isObjectLiteralExpression(node)){const result={};for(const p of node.properties)if(ts.isPropertyAssignment(p))result[p.name.getText(sf).replace(/^['"]|['"]$/g,'')]=value(p.initializer);return result}return undefined}
 function walk(node){
  if(ts.isCallExpression(node)&&node.expression.getText(sf)==='copy'&&node.arguments.length===2&&ts.isStringLiteral(node.arguments[0])&&ts.isStringLiteral(node.arguments[1]))check(node.arguments[0].text,node.arguments[1].text,file);
  if(ts.isVariableDeclaration(node)&&node.name.getText(sf)==='pages'&&node.initializer){for(const [section,page] of Object.entries(value(node.initializer))){check(page.title,page.ar,section);check(page.intro,page.introAr,section);for(const row of page.items||[]){check(row[0],row[1],section);check(row[2],row[3],section)}}}
  if(ts.isVariableDeclaration(node)&&node.name.getText(sf)==='steps'&&node.initializer)for(const row of value(node.initializer)){check(row[0],row[1],'Journey');check(row[2],row[3],'Journey')}
  if(ts.isVariableDeclaration(node)&&node.name.getText(sf)==='nav'&&node.initializer)for(const row of value(node.initializer))check(row[1],row[2],'Navigation');
  if(ts.isArrayLiteralExpression(node)){const rows=value(node);if(Array.isArray(rows)&&rows.length&&rows.every(r=>Array.isArray(r)&&r.length===3&&typeof r[0]==='string'&&typeof r[1]==='string'&&typeof r[2]==='string'))for(const row of rows)check(row[1],row[2],'Footer')}
  ts.forEachChild(node,walk);
 }walk(sf);
}
for(const id of ['sample.overall','sample.governance','sample.execution','sample.quality'])if(!catalogue[id]){console.error('Missing sample entry:',id);failures++}
if(failures)process.exitCode=1;else console.log(`Verified ${checked} public copy lookups and sample-score entries.`);
