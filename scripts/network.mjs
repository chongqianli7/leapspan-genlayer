import {createClient} from 'genlayer-js'
import {studionet} from 'genlayer-js/chains'
import {TransactionStatus, transactionsStatusNumberToName} from 'genlayer-js/types'

export const chain = studionet
export const client = createClient({chain})
export const explorer = 'https://explorer-studio.genlayer.com'
export async function finalized(hash) {
  const deadline = Date.now() + 300000
  while (Date.now() < deadline) {
    let receipt
    try {
      receipt = await client.getTransaction({hash})
    } catch {
      // A transient RPC or indexing failure does not invalidate the submitted hash.
    }
    if (receipt && outcome(receipt, hash).status === TransactionStatus.FINALIZED) return receipt
    await new Promise(resolve => setTimeout(resolve, 4500))
  }
  throw new Error('Finalization timed out for ' + hash)
}
export function outcome(receipt, hash) {
  const vote = receipt.consensus_data?.leader_receipt?.[0]
  const execution = receipt.txExecutionResultName ?? vote?.execution_result
  const observed = Object.values(vote?.eq_outputs ?? {})[0]?.payload?.readable
  let reason = vote?.result?.payload?.readable ?? vote?.error ?? null
  if (execution === 'ERROR' && typeof observed === 'string' && /^[A-Z_0-9]+$/.test(observed.replaceAll('"', ''))) {
    reason = observed.replaceAll('"', '')
  }
  return {
    hash,
    status: receipt.statusName ?? transactionsStatusNumberToName[receipt.status] ?? receipt.status,
    consensus: receipt.result_name ?? receipt.resultName,
    execution: execution === 'FINISHED_WITH_RETURN' ? 'SUCCESS' : execution,
    reason: execution === 'SUCCESS' || execution === 'FINISHED_WITH_RETURN' ? null : reason,
  }
}
