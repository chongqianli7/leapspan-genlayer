import {existsSync,readFileSync,writeFileSync} from 'node:fs'
import {createAccount} from 'genlayer-js'
import {chain,client,finalized,outcome} from './network.mjs'
if(process.argv[2]==='--record' && existsSync('deployment.json')) throw Error('Deployment record already exists')
if(chain.id!==61999 || await client.getChainId()!==61999) throw Error('Wrong network')
const hash=await client.deployContract({account:createAccount(),code:readFileSync('contracts/leapspan.py','utf8'),args:[]})
console.log('Submitted',hash)
const receipt=await finalized(hash)
const record={...outcome(receipt,hash),address:receipt.to_address,chainId:61999}
console.log(record)
if(record.status!=='FINALIZED'||record.execution!=='SUCCESS') process.exit(1)
if(process.argv[2]==='--record') writeFileSync('deployment.json',JSON.stringify(record,null,2)+'\n',{flag:'wx'})
