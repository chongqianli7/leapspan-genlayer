import {TransactionHashVariant} from 'genlayer-js/types'
import {abi} from 'genlayer-js'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import {client, finalized, outcome} from './network.mjs'

const hash = text => createHash('sha256').update(text).digest('hex')
const methods = {
  "dual_source_snapshot": "refresh",
  "across_2016_leap_second": "certify",
  "replay_same_certificate": "certify",
  "outside_source_horizon": "certify"
}
const deployment = JSON.parse(readFileSync('deployment.json'))
const {transactions, finalState} = JSON.parse(readFileSync('evidence.json'))
assert.equal(await client.getChainId(),61999)
const deployed = await finalized(deployment.hash)
assert.equal(outcome(deployed,deployment.hash).execution,'SUCCESS')
assert.equal(deployed.to_address.toLowerCase(),deployment.address.toLowerCase())
for(const saved of transactions){
  const tx=await finalized(saved.hash)
  const record=outcome(tx,saved.hash)
  for(const field of ['status','execution','consensus','reason']) assert.deepEqual(record[field],saved[field])
  assert.equal(record.status,'FINALIZED')
  const call=abi.calldata.decode(Buffer.from(tx.data.calldata.base64,'base64'))
  assert.equal(call.get('method'),methods[saved.label])
  assert.equal(tx.from_address.toLowerCase(),saved.signer)
  assert.equal(tx.to_address.toLowerCase(),deployment.address.toLowerCase())
}
const read=async (functionName,args)=>JSON.parse(await client.readContract({
  address:deployment.address,functionName,args,transactionHashVariant:TransactionHashVariant.LATEST_FINAL,
}))
const {digest,key,certificate}=finalState
const snapshot=await read('snapshot',[digest])
assert.equal(hash(JSON.stringify(snapshot)),digest)
assert.equal(hash(digest+':'+certificate.start+':'+certificate.end),key)
assert.deepEqual(await read('certificate',[key]),certificate)
const [rows,expiry]=snapshot
const offset=stamp=>rows.findLast(row=>row[0]<=stamp)[1]
assert.equal(expiry,finalState.expiresExclusive)
assert.equal(certificate.elapsed_seconds,certificate.end-certificate.start+offset(certificate.end)-offset(certificate.start))
assert.equal(certificate.elapsed_seconds,2)
assert.equal(transactions[1].returnValue,transactions[2].returnValue)
console.log(JSON.stringify({verifiedReceipts:transactions.length+1,certificate},null,2))
