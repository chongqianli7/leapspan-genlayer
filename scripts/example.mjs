import assert from 'node:assert/strict'
import {createAccount} from 'genlayer-js'
import {session} from './session.mjs'

const {read,send,finish}=session()
const wallet=createAccount()
const digest=await send('dual_source_snapshot','refresh',[],wallet)
assert.match(digest,/^[0-9a-f]{64}$/)
const snapshot=await read('snapshot',[digest])
assert(snapshot[0].some(([stamp,offset])=>stamp===1483228800&&offset===37))
const start=1483228799n
const end=1483228800n
const key=await send('across_2016_leap_second','certify',[digest,start,end],wallet)
assert.equal(await send('replay_same_certificate','certify',[digest,start,end],wallet),key)
await send('outside_source_horizon','certify',[digest,BigInt(snapshot[1])-1n,BigInt(snapshot[1])],wallet,'ERROR')
const certificate=await read('certificate',[key])
assert.deepEqual(certificate,{
  snapshot:digest,start:Number(start),end:Number(end),posix_seconds:1,adjustment:1,
  elapsed_seconds:2,transitions:[[1483228800,37]],
})
finish({digest,key,certificate,transitionCount:snapshot[0].length,expiresExclusive:snapshot[1]})
