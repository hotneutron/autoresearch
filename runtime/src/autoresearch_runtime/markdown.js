/* Safe local Markdown subset for immutable evidence. No HTML/images/resources.
 * Revision History: 2026-10-12 — rendered source reports with exact raw fallback.
 */
function markdownEscape(value){return String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function markdownLink(href){
  if(/[\u0000-\u0020\u007f]/.test(href))return null;
  if(!/^https?:\/\//i.test(href))return null;
  try{const url=new URL(href);return ['https:','http:'].includes(url.protocol)?url.href:null;}catch{return null;}
}
function markdownInline(value,depth=0){
  if(depth>8)return markdownEscape(value);
  // Tokenize original text once; generated markup is never parsed as Markdown.
  const pattern=/(`+)([^`\n]+?)\1|(!?)\[([^\]\n]*)\]\(([^\s)]+)(?:\s+"[^"\n]*")?\)|\*\*([^\n]+?)\*\*|__([^\n]+?)__|~~([^\n]+?)~~|\*([^*\n]+?)\*|_([^_\n]+?)_|\\([\\`*{}_\[\]()#+.!|>-])/g;
  let result='',last=0,match;
  while((match=pattern.exec(value))){
    result+=markdownEscape(value.slice(last,match.index));
    if(match[1])result+='<code>'+markdownEscape(match[2])+'</code>';
    else if(match[4]!==undefined){
      const label=markdownInline(match[4],depth+1),url=markdownLink(match[5]);
      // Images are explicit text: never fetch external or local resources.
      result+=match[3]?'['+label+']':url?'<a href="'+markdownEscape(url)+'" target="_blank" rel="noopener noreferrer">'+label+'</a>':label+' <span class="markdown-inert">('+markdownEscape(match[5])+')</span>';
    }else if(match[6]!==undefined||match[7]!==undefined)result+='<strong>'+markdownInline(match[6]??match[7],depth+1)+'</strong>';
    else if(match[8]!==undefined)result+='<del>'+markdownInline(match[8],depth+1)+'</del>';
    else if(match[9]!==undefined||match[10]!==undefined)result+='<em>'+markdownInline(match[9]??match[10],depth+1)+'</em>';
    else result+=markdownEscape(match[11]);
    last=pattern.lastIndex;
  }
  return result+markdownEscape(value.slice(last));
}
function markdownCells(line){
  line=line.trim();if(line.startsWith('|'))line=line.slice(1);if(line.endsWith('|')&&!line.endsWith('\\|'))line=line.slice(0,-1);
  const cells=[];let text='',escaped=false,ticks=0;
  for(let i=0;i<line.length;i++){
    const c=line[i];
    if(escaped){text+='\\'+c;escaped=false;continue;}
    if(c==='\\'){escaped=true;continue;}
    if(c==='`'){let end=i;while(line[end]==='`')end++;const count=end-i;ticks=ticks===count?0:ticks||count;text+=line.slice(i,end);i=end-1;continue;}
    if(c==='|'&&!ticks){cells.push(text.trim());text='';}else text+=c;
  }
  if(escaped)text+='\\';cells.push(text.trim());return cells;
}
function renderMarkdown(raw,depth=0){
  if(depth>12)return '<pre>'+markdownEscape(raw)+'</pre>';
  const lines=String(raw).replace(/\r\n?/g,'\n').split('\n');let out='',i=0;
  const fence=line=>line.match(/^ {0,3}(`{3,}|~{3,})([^\n]*)$/);
  const heading=line=>line.match(/^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$/);
  const list=line=>line.match(/^(\s*)([-+*]|\d+[.)])\s+(.*)$/);
  const divider=line=>/^ {0,3}(?:\*\s*){3,}$|^ {0,3}(?:-\s*){3,}$|^ {0,3}(?:_\s*){3,}$/.test(line);
  const tableSeparator=line=>{const cells=markdownCells(line);return cells.length>0&&cells.every(c=>/^:?-{3,}:?$/.test(c));};
  const block=index=>fence(lines[index])||heading(lines[index])||list(lines[index])||/^ {0,3}>/.test(lines[index])||divider(lines[index]);
  while(i<lines.length){
    const line=lines[i];if(!line.trim()){i++;continue;}
    const f=fence(line);
    if(f){const code=[];i++;const close=new RegExp('^ {0,3}'+f[1][0]+'{'+f[1].length+',}\\s*$');while(i<lines.length&&!close.test(lines[i]))code.push(lines[i++]);if(i<lines.length)i++;out+='<pre><code>'+markdownEscape(code.join('\n'))+'</code></pre>';continue;}
    const h=heading(line);if(h){out+='<h'+h[1].length+'>'+markdownInline(h[2])+'</h'+h[1].length+'>';i++;continue;}
    if(i+1<lines.length&&/^ {0,3}(?:=+|-+)\s*$/.test(lines[i+1])){const level=lines[i+1].trim()[0]==='='?1:2;out+='<h'+level+'>'+markdownInline(line.trim())+'</h'+level+'>';i+=2;continue;}
    if(divider(line)){out+='<hr>';i++;continue;}
    if(/^ {0,3}>/.test(line)){const quote=[];while(i<lines.length&&/^ {0,3}>/.test(lines[i]))quote.push(lines[i++].replace(/^ {0,3}>\s?/,''));out+='<blockquote>'+renderMarkdown(quote.join('\n'),depth+1)+'</blockquote>';continue;}
    if(i+1<lines.length&&line.includes('|')&&tableSeparator(lines[i+1])){
      const headers=markdownCells(line),separators=markdownCells(lines[i+1]);
      if(headers.length===separators.length){
        const alignment=separators.map(c=>c.startsWith(':')&&c.endsWith(':')?'center':c.endsWith(':')?'right':'left');
        out+='<div class="table-scroll"><table><thead><tr>'+headers.map((c,j)=>'<th style="text-align:'+alignment[j]+'">'+markdownInline(c)+'</th>').join('')+'</tr></thead><tbody>';i+=2;
        while(i<lines.length&&lines[i].trim()&&lines[i].includes('|')){const cells=markdownCells(lines[i++]);out+='<tr>'+headers.map((_,j)=>'<td style="text-align:'+alignment[j]+'">'+markdownInline(cells[j]??'')+'</td>').join('')+'</tr>';}
        out+='</tbody></table></div>';continue;
      }
    }
    const l=list(line);
    if(l){const indent=l[1].length,ordered=/^\d/.test(l[2]),tag=ordered?'ol':'ul';out+='<'+tag+'>';
      while(i<lines.length){const current=list(lines[i]);if(!current||current[1].length!==indent||/^\d/.test(current[2])!==ordered)break;
        let body=current[3];i++;const nested=[];
        while(i<lines.length&&lines[i].trim()&&((list(lines[i])?.[1].length??0)>indent||(!list(lines[i])&&new RegExp('^ {'+(indent+2)+'}').test(lines[i]))))nested.push(lines[i++].slice(indent+2));
        const task=body.match(/^\[([ xX])\]\s+(.*)$/);if(task)body=(task[1]===' '?'☐ ':'☑ ')+task[2];
        out+='<li>'+markdownInline(body)+(nested.length?renderMarkdown(nested.join('\n'),depth+1):'')+'</li>';
      }
      out+='</'+tag+'>';continue;
    }
    if(/^ {4}\S/.test(line)){const code=[];while(i<lines.length&&/^ {4}/.test(lines[i]))code.push(lines[i++].slice(4));out+='<pre><code>'+markdownEscape(code.join('\n'))+'</code></pre>';continue;}
    const para=[line.trim()];i++;
    while(i<lines.length&&lines[i].trim()&&!block(i)&&!(i+1<lines.length&&lines[i].includes('|')&&tableSeparator(lines[i+1])))para.push(lines[i++].trim());
    out+='<p>'+para.map(text=>markdownInline(text)).join('<br>')+'</p>';
  }
  return out;
}
