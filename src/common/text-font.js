const missing="躙";
export function textFont(text){
  const value=String(text||'');for(let i=0;i<missing.length;i++)if(value.indexOf(missing[i])>=0)return 'stellaextra';return 'sans-serif';
}
