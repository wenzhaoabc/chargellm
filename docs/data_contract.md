# Data Contract

## Raw Sample

Each battery sample contains:

- `battery_id`: string
- `label`: one of `电池故障`, `电池老化`, `非标电池`, `正常`
- `reason`: optional string, present in SFT data
- `charging_process`: list of charging process objects

Each charging process contains:

- `process_id`: string
- `charge_start_time`: optional string
- `charge_end_time`: optional string
- `current_series`: list of float
- `voltage_series`: list of float
- `power_series`: list of float
- `charge_capacity`: list of float

## Canonical In-Memory Sample

Each model sample should be normalized into:

- `battery_id`
- `label_id`
- `label_text`
- `reason_text`
- `process_ids`
- `process_values`: tensor-like array with shape `[num_processes, seq_len, 4]`
- `process_mask`: shape `[num_processes, seq_len]`
- `history_mask`: shape `[num_processes]`

Channel order is fixed:

1. current
2. voltage
3. power
4. charge_capacity

## Batch Contract

The collator returns:

- `battery_ids`: list[str]
- `process_ids`: list[list[str]]
- `inputs`: float tensor `[batch, num_processes, seq_len, num_channels]`
- `process_mask`: bool tensor `[batch, num_processes, seq_len]`
- `history_mask`: bool tensor `[batch, num_processes]`
- `labels`: long tensor `[batch]`
- `reasons`: list[str]

## Split Rule

Train, validation, and test splits must be grouped by `battery_id`.

No battery may appear in more than one split.

## Output Contract

The generated diagnosis object must contain:

- `label`: string
- `confidence`: float in `[0, 1]`
- `key_processes`: list[str]
- `explanation`: string