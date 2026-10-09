"""Keep physical simulation integrity separate from arrived-cohort accounting."""


def merge_integrity(metadata, metrics):
    result={**metadata,**metrics}
    reasons=list(metadata.get('invalid_reasons',[]))
    if metadata.get('invalid_reason'):
        reasons.append(str(metadata['invalid_reason']))
    if metadata.get('valid') is False or metadata.get('integrity_valid') is False:
        reasons.append('manifest_declared_invalid')
    collision_counts=[]
    for container in [metadata,metadata.get('final_counts',{})]:
        if 'collisions' in container:
            count=container['collisions']
            if type(count) is not int or count<0:
                raise ValueError('collision evidence must be a nonnegative integer')
            collision_counts.append(count)
    if any(collision_counts):
        reasons.append('collision_evidence')
    teleport_counts=[]
    for container in [metadata,metadata.get('final_counts',{})]:
        for field in ['teleported','teleports']:
            if field in container:
                count=container[field]
                if type(count) is not int or count<0:
                    raise ValueError('teleport evidence must be a nonnegative integer')
                teleport_counts.append(count)
    if any(teleport_counts): reasons.append('teleport_evidence')
    real=metadata.get('data_source')=='sumo'
    if real and not collision_counts:
        reasons.append('collision_evidence_missing')
    if real and not teleport_counts:
        reasons.append('teleport_evidence_missing')
    if not metrics['valid']:
        reasons.append('cohort_incomplete_removed_or_teleported')
    reasons=list(dict.fromkeys(reasons))
    result.update(cohort_complete=metrics['complete'],cohort_valid=metrics['valid'],
                  integrity_verified=bool(collision_counts) and bool(teleport_counts),
                  simulation_integrity_valid=not any(collision_counts) and not any(teleport_counts) and not any(
                      reason!='cohort_incomplete_removed_or_teleported' for reason in reasons),
                  invalid_reasons=reasons,invalid_reason=';'.join(reasons) if reasons else None,
                  valid=metrics['valid'] and not reasons)
    if not result['valid']:
        result.update(mean_journey_s=None,p95_journey_s=None,co2_kg_final=None)
    return result
