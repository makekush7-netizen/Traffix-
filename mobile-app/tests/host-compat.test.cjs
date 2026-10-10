const { test } = require('node:test');
const assert = require('node:assert/strict');
const { TrafficClient } = require('./load-client.cjs');
test('v2 host without capabilities is discovered without an operator map or claim', async t => {
 const previous=global.fetch, calls=[];
 global.fetch=async url=>{calls.push(url);return url.endsWith('/openapi.json')?{ok:true,status:200,json:async()=>({paths:{'/api/v2/phones/claim':{post:{}},'/api/v2/phones/state':{get:{}}}})}:{ok:false,status:404,json:async()=>({detail:'Not Found'})};};
 t.after(()=>{global.fetch=previous;});
 const client=new TrafficClient(()=>{},()=>{});
 assert.equal(await client.configure('http://192.168.137.1:8006'),null);
 assert.equal(client.apiVersion,'2.0');
 assert.deepEqual(calls,['http://192.168.137.1:8006/api/v2/capabilities','http://192.168.137.1:8006/openapi.json']);
});
