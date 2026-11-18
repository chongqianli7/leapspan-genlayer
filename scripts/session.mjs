import assert from 'node:assert/strict'
import {readFileSync, writeFileSync} from 'node:fs'
import {client, finalized, outcome} from './network.mjs'

export function session() {
  const deployment = JSON.parse(readFileSync('deployment.json'))
  assert.equal(deployment.chainId, 61999)
  const evidence = {deployment, transactions:[]}
  const destination = process.argv.includes('--record') ? 'evidence.json' : null
  if (destination) writeFileSync(destination, JSON.stringify(evidence,null,2)+'\n',{flag:'wx'})
  const save = () => {
    if (destination) writeFileSync(destination, JSON.stringify(evidence,null,2)+'\n')
  }
  const read = async (functionName,args) => {
    const raw = await client.readContract({address:deployment.address,functionName,args,stateStatus:'finalized'})
    return raw ? JSON.parse(raw) : null
  }
  async function send(label, functionName, args, account, expected='SUCCESS') {
    const hash = await client.writeContract({address:deployment.address,functionName,args,account,value:0n})
    const row = {label, hash, signer:account.address.toLowerCase()}
    evidence.transactions.push(row)
    save()
    console.log(label, 'submitted', hash)
    const tx = await finalized(hash)
    Object.assign(row,outcome(tx,hash))
    const result = tx.consensus_data?.leader_receipt?.[0]?.result?.payload?.readable
    if (result && result !== 'null') row.returnValue = JSON.parse(result)
    save()
    console.log(label,row.status,row.execution,row.reason??'')
    assert.equal(row.status,'FINALIZED')
    assert.equal(row.consensus,'MAJORITY_AGREE')
    assert.equal(row.execution,expected)
    return row.returnValue
  }
  return {read,send,finish(state){ evidence.finalState=state; save(); console.log(JSON.stringify(state)) }}
}
