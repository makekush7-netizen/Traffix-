import {test} from 'node:test';
import assert from 'node:assert/strict';
import {vehicleClickGesture,nearbyVehicles} from './vehicle-picking.mjs';

const pointer=(x,y,extra={})=>({clientX:x,clientY:y,pointerId:1,button:0,isPrimary:true,...extra});

test('a primary click picks the released screen position',()=>{
 const picked=[],gesture=vehicleClickGesture(p=>picked.push(p));
 gesture.down(pointer(20,30));gesture.up(pointer(21,30));
 assert.deepEqual(picked,[{x:21,y:30}]);
});

test('orbit drag never becomes a click even after returning to its origin',()=>{
 const picked=[],gesture=vehicleClickGesture(p=>picked.push(p));
 gesture.down(pointer(20,30));gesture.move(pointer(40,30));gesture.up(pointer(20,30));
 assert.equal(picked.length,0);
});

test('pan modifiers, secondary buttons, another pointer and cancellation do not pick',()=>{
 for(const extra of [{button:2},{shiftKey:true},{ctrlKey:true},{metaKey:true},{isPrimary:false}]){
  const picked=[],gesture=vehicleClickGesture(p=>picked.push(p));
  gesture.down(pointer(20,30,extra));gesture.up(pointer(20,30,extra));
  assert.equal(picked.length,0);
 }
 const picked=[],gesture=vehicleClickGesture(p=>picked.push(p));
 gesture.down(pointer(20,30));gesture.up(pointer(20,30,{pointerId:2}));
 gesture.cancel();gesture.up(pointer(20,30));assert.equal(picked.length,0);
 gesture.down(pointer(20,30));gesture.down(pointer(20,30,{pointerId:2,isPrimary:false}));
 gesture.up(pointer(20,30));assert.equal(picked.length,0);
});

test('small on-screen targets are ranked by distance then depth; hidden and clipped targets reject',()=>{
 const candidates=[{id:'far',x:105,y:100,z:.5},{id:'front',x:105,y:100,z:.2},
  {id:'hidden',x:100,y:100,z:.1,visible:false},{id:'behind',x:100,y:100,z:2},
  {id:'invalid',x:NaN,y:100,z:.1},{id:'outside',x:130,y:100,z:.1}];
 assert.deepEqual(nearbyVehicles({x:100,y:100},candidates).map(c=>c.id),['front','far']);
 assert.deepEqual(nearbyVehicles({x:0,y:0},candidates),[]);
});
