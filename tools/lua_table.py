"""Parse literal Lua tables as data; no Lua code is ever executed."""
import re,json
TOK=re.compile(r'\s+|--\[\[.*?\]\]|--[^\n]*|\[\[.*?\]\]|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[-+]?\d+(?:\.\d+)?|[^\W\d]\w*|[{}\[\]=,;]',re.S|re.U)
class Parser:
    def __init__(self,s):
        self.t=[];pos=0
        for m in TOK.finditer(s):
            if s[pos:m.start()].strip():raise ValueError('Not a literal table: '+repr(s[pos:m.start()][:80]))
            x=m.group();pos=m.end()
            if not x.isspace() and not x.startswith('--'):self.t.append(x)
        if s[pos:].strip():raise ValueError('Trailing nonliteral data')
        self.p=0
    def take(self):
        x=self.t[self.p];self.p+=1;return x
    def want(self,x):
        actual=self.take()
        if actual!=x:raise ValueError('Expected '+x+' got '+actual)
    def value(self):
        x=self.take()
        if x=='{':
            result={};i=1
            while self.t[self.p]!='}':
                token=self.t[self.p]
                if token=='[':
                    self.take();key=self.value();self.want(']');self.want('=');value=self.value()
                elif self.p+1<len(self.t) and self.t[self.p+1]=='=':
                    key=self.take();self.take();value=self.value()
                else:key=i;i+=1;value=self.value()
                if key in result:raise ValueError('Duplicate table key '+str(key))
                result[key]=value
                if self.t[self.p] in [',',';']:self.take()
            self.want('}');return result
        if x.startswith('[['):return x[2:-2]
        if x.startswith(('"',"'")):
            body=x[1:-1]
            def escape(m):
                v=m.group(1)
                if v.isdigit():return chr(int(v))
                return {'n':'\n','r':'\r','t':'\t','\\':'\\','"':'"',"'":"'",'\n':'\n'}.get(v,v)
            return re.sub(r'\\(\d{1,3}|.)',escape,body,flags=re.S)
        if x=='true':return True
        if x=='false':return False
        if x=='nil':return None
        if re.fullmatch(r'[-+]?\d+(?:\.\d+)?',x):return float(x) if '.' in x else int(x)
        raise ValueError('Nonliteral Lua value '+x)
    def assignments(self):
        out={}
        while self.p<len(self.t):
            key=self.take();self.want('=');out[key]=self.value()
        return out
def parse(s):return Parser(s).assignments()
def array(t):return [v for k,v in sorted(((k,v) for k,v in t.items() if isinstance(k,int)),key=lambda kv:kv[0])]
