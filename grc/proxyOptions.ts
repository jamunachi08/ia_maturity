import type {IncomingMessage} from 'node:http';
export default {
 '^/(api|assets|files|private)': {
  target: 'http://127.0.0.1:8005',ws:false,
  configure: (proxy:any) => proxy.on('proxyReq',(request:any,_req:IncomingMessage)=>request.setHeader('X-Frappe-Site-Name','grc.local'))
 }
};
