# Multi-Task Vision-Language Model for Fill-Level Estimation in Autonomous Heavy Machinery

## Master's Thesis Project

### Working Thesis Direction

**Multi-Task Vision-Language Modeling for Visual Fill-Level Estimation in Autonomous Heavy Machinery**

This master's thesis investigates whether a Vision-Language Model (VLM) can learn to estimate multiple industrial material-handling states from camera images, with a focus on autonomous and semi-autonomous heavy machinery operating in mining, quarrying, underground, and material-handling environments.

The broader objective is not limited to a single crusher-fill task. The intended system should eventually learn multiple visually related tasks such as:

- Crusher fill level
- Shovel / bucket fill level
- Material pile quantity / pile fill level
- Dumping or unloading-area fill state

Each task is represented primarily as a continuous percentage from **0% to 100%**, where the exact physical meaning of the percentage is defined separately for each task.

The long-term goal is to evaluate whether one shared multimodal model can learn these related tasks instead of maintaining a completely separate perception model for every individual use case.

---

# 1. Project Motivation

Heavy machinery operating in industrial environments continuously interacts with large quantities of material.

Examples include:

- Excavators filling a shovel or bucket
- Loaders transporting material
- Trucks dumping material
- Crushers receiving material
- Material accumulating in piles
- Dumping zones becoming empty or full

Automation systems often require an estimate of how much material is currently present.

A simplified example is:

```text
Crusher:
0%   = completely empty
50%  = approximately half full
100% = completely full

Similar continuous representations can be defined for the other tasks.
Traditional solutions may use dedicated sensor-processing pipelines, geometric reconstruction, LiDAR processing, depth estimation, or task-specific perception networks.
This thesis explores a different question:
Can a general-purpose Vision-Language Model learn to visually reason about material quantity across several related industrial tasks?

Instead of building one independent model for:
crusher fill

another for:
shovel fill

and another for:
pile quantity

the aim is to investigate whether a shared VLM can learn:
images + task instruction
        ↓
shared visual understanding
        ↓
task-specific percentage estimate

2. Core Thesis Idea
The project is formulated as a multi-task visual estimation problem.
A model receives one or more camera images together with a textual instruction.
Conceptually:
Camera image(s)
      +
Task prompt
      ↓
Vision-Language Model
      ↓
Percentage estimate

For example:
Task:
Estimate the crusher fill level.

Images:
front_narrow.jpg
front_wide.jpg

Output:
63%

Another task could use the same model:
Task:
Estimate how full the shovel is.

Image:
shovel_camera.jpg

Output:
78%

Another:
Task:
Estimate the amount of material in the pile.

Image(s):
pile camera view(s)

Output:
42%

The model therefore learns both:
1. visual understanding of material quantity;
2. which industrial task is currently being requested.
3. Main Multi-Task Targets
3.1 Crusher Fill-Level Estimation
This is the most developed task in the current thesis pipeline.
The model receives two synchronized camera views:
front_narrow
front_wide

and predicts:
0–100%

Example:
Input:
front_narrow image
front_wide image

Prompt:
Estimate the fill level of the industrial crusher shown in the two images.
Use visual information from both images.
The fill level is a percentage from 0 to 100,
where 0 means completely empty and 100 means completely full.
Return only the estimated percentage.

Target:
63%

The current ground-truth source is:
/processing/crusher/fill_level

The value is generated using Sensmore's existing LiDAR-based processing pipeline.
For the thesis, this value is currently treated as the reference ground truth.
Example:
fill_level = 25

means approximately:
25% full

3.2 Shovel / Bucket Fill-Level Estimation
The second intended task is estimating how much material is currently inside a shovel or bucket.
Conceptually:
0%   = empty shovel
25%  = lightly filled
50%  = approximately half full
75%  = mostly full
100% = full

A future training sample may look like:
Task:
shovel_fill_level

Image:
shovel_camera.jpg

Ground truth:
74%

Possible prompt:
Estimate the fill level of the shovel shown in the image.
The value must be between 0 and 100 percent.
Return only the estimated percentage.

The exact ground-truth generation method must remain consistent with the company's labeling pipeline.
This task has not yet gone through the same complete extraction, synchronization, manual-QC, and benchmarking pipeline as the crusher task.
3.3 Material Pile Quantity / Pile Fill-Level
Another intended task is visual estimation of the amount of material present in a pile.
The output is again represented as a normalized percentage.
Conceptually:
0%   = no significant material
25%  = small pile
50%  = medium quantity
75%  = large pile
100% = reference maximum pile quantity / capacity

A possible sample:
Task:
pile_fill_level

Image:
pile_view.jpg

Target:
58%

The exact interpretation of 100% must be defined consistently.
For example, 100% could represent:
maximum expected pile volume

or:
maximum safe operational pile size

or another normalized reference used by Sensmore.
This definition must come from the company's ground-truth / automatic-labeling pipeline rather than being invented by the VLM.
3.4 Dumping / Unloading-Area Fill Estimation
The fourth intended task concerns the material quantity currently present in a dumping or unloading zone.
Examples include:
crusher dumping area
truck unloading zone
material receiving area
stockpile unloading region

Conceptually:
0%   = empty
50%  = approximately half of reference capacity
100% = full / reference maximum

The model may receive one or multiple camera views and predict:
dumping_area_fill = 67%

Possible prompt:
Estimate how full the dumping or unloading area is.
Return a percentage between 0 and 100.
Return only the percentage.

4. Why Multi-Task Learning?
The individual tasks are different, but visually they share important characteristics.
All involve reasoning about:
material quantity
material geometry
visible occupied area
pile height
pile shape
container boundaries
empty vs occupied regions
relative capacity

Therefore, representations learned from one task may potentially help another.
A shared VLM could conceptually learn:
                   ┌─ Crusher fill
                   │
Images → VLM ──────┼─ Shovel fill
                   │
                   ├─ Pile quantity
                   │
                   └─ Dumping-area fill

The research question is not merely whether a VLM can solve one task.
A more interesting thesis question is:
Can one multimodal model learn several industrial material-quantity estimation tasks using shared visual representations?

This is the primary motivation behind the multi-task direction.
5. Proposed Model Interface
A general training sample can be represented as:
{
    task: "crusher_fill_level",
    images: [
        front_narrow.jpg,
        front_wide.jpg
    ],
    prompt:
        "Estimate the exact crusher fill level from 0 to 100 percent.",
    target:
        "63%"
}

Another sample could be:
{
    task: "shovel_fill_level",
    images: [
        shovel_camera.jpg
    ],
    prompt:
        "Estimate the exact shovel fill level from 0 to 100 percent.",
    target:
        "78%"
}

Another:
{
    task: "pile_fill_level",
    images: [
        pile_camera.jpg
    ],
    prompt:
        "Estimate the amount of material in the pile as a percentage.",
    target:
        "42%"
}

This allows one model to receive a task instruction and infer the appropriate output.
6. Current Dataset Status
The most mature dataset currently belongs to the:
crusher_fill_level

task.
Current Final Visually-QC-Clean Daylight Dataset
Samples:               5,401 paired samples
Recordings:            34
Camera views/sample:   2
Individual images:     10,802
Fill range:            0–100%

Each sample consists of:
1 fill-level ground-truth value
1 front_narrow image
1 front_wide image
timestamp information
synchronization information
recording provenance

The persistent dataset currently consists of:
JPEG images
+
CSV metadata

The images are not permanently stored as PyTorch tensors.
Tensors are expected to be generated later by the model's image processor during training.
7. Current Crusher Fill Distribution
The final visually clean daylight dataset contains:
00–10%   : 148 samples
11–20%   : 195 samples
21–30%   : 322 samples
31–40%   : 481 samples
41–50%   : 617 samples
51–60%   : 509 samples
61–70%   : 914 samples
71–80%   : 951 samples
81–90%   : 414 samples
91–100%  : 850 samples

Total:
5,401 samples

The dataset currently contains significantly more high-fill than low-fill observations.
Particularly limited:
0–10%
11–20%
21–30%

The 0–20% region contains only:
343 samples

which represents approximately:
6.35% of the current clean dataset

8. Dataset Collection Target
The current collection strategy uses ten monitoring ranges:
0–10%
11–20%
21–30%
31–40%
41–50%
51–60%
61–70%
71–80%
81–90%
91–100%

The working data-acquisition target is:
>= 1,000 clean samples per range

giving approximately:
10 ranges × 1,000 samples
≈ 10,000 clean paired samples

This is primarily a dataset-coverage goal.
The exact percentage remains the model target.
For example:
Bucket used for dataset monitoring:
60–70%

Actual training target:
63%

The model is therefore not necessarily trained to output:
60–70%

Instead it should still predict:
63%

The ranges help monitor coverage and imbalance.
9. Current Dataset Deficit
Relative to the 1,000-sample-per-range collection goal:
Range      Current      Additional needed

0–10%        148              852
11–20%       195              805
21–30%       322              678
31–40%       481              519
41–50%       617              383
51–60%       509              491
61–70%       914               86
71–80%       951               49
81–90%       414              586
91–100%      850              150

Total theoretical deficit:
4,599 clean samples

if exactly 1,000 samples per range are required.
The highest data-acquisition priorities are currently:
0–10%
11–20%
21–30%

followed by:
81–90%
31–40%
51–60%

10. Why Train / Validation / Test Is Not Frozen Yet
The project is still in the dataset-collection phase.
The current decision is:
DO NOT freeze train/validation/test yet.

Reasons:
1. The target dataset size has not yet been reached.
2. Several fill ranges remain strongly underrepresented.
3. Additional recordings are expected over the coming weeks.
4. The final split should preserve complete weeks/sessions to avoid temporal leakage.
5. Locking the split now may create severe distribution imbalance in future validation or test sets.
Therefore, current samples should remain:
split = UNASSIGNED

until the collection target is sufficiently satisfied.
11. Temporal Leakage
The MCAP files are not necessarily independent experiments.
Some MCAPs may simply be chunks of a longer machine recording session.
For example:
Week 1
   ├── MCAP A
   ├── MCAP B
   ├── MCAP C
   └── MCAP D

Randomly assigning:
MCAP A → train
MCAP B → validation

may still introduce temporal leakage because the recordings could contain:
same machine
same operating sequence
same environment
same material
same lighting
neighboring time periods

Therefore, the final split should preferably operate at:
week level

or at minimum:
independent session level

rather than individual-image level.
A future split could conceptually be:
Weeks 1 + 2 → TRAIN
Week 3      → VALIDATION
Week 4      → TEST

The exact split will be determined after sufficient data has been collected.
12. Dataset Provenance
Every sample should retain enough information to trace it back to the original recording.
Important metadata fields include:
recording_id
source_mcap
sample
task
front_narrow
front_wide
fill_level
fill_timestamp_ns
narrow_timestamp_ns
wide_timestamp_ns
narrow_delta_t_seconds
wide_delta_t_seconds
week_id
session_id
domain
qc_status
split

Future multi-task datasets should additionally include:
task_name
task_prompt
target_percentage
label_source

For example:
task_name = crusher_fill_level

or:
task_name = shovel_fill_level

13. Current Crusher Synchronization Method
Ground-truth and camera frames are synchronized using ROS:
header.stamp

and not MCAP log time.
For every crusher fill-level message:
t_GT

the pipeline independently selects:
nearest front_narrow frame
nearest front_wide frame

Current acceptance rule:
|t_GT - t_narrow| <= 1.0 s

|t_GT - t_wide| <= 1.0 s

There is currently no independent narrow-to-wide threshold.
14. Observed Synchronization Characteristics
For the final 5,401 visually clean crusher samples:
Median narrow-wide difference : 0.403255 s
P95                           : 1.319773 s
P99                           : 1.713107 s
Maximum                       : 1.960111 s

The approximately two-second maximum occurs because each camera can independently be almost one second away from the same ground-truth timestamp in opposite temporal directions.
Example:
Narrow                GT                 Wide

-0.998 s            0.000 s            +0.962 s

<------------ approximately 1.96 s ------------>

This synchronization characteristic should be investigated further before changing the established 1-second camera-to-ground-truth rule.
15. Crusher Dataset Extraction Pipeline
The current pipeline is:
RAW MCAPs
    ↓
identify DAY / NIGHT recordings
    ↓
scan fill-level messages
    ↓
read /processing/crusher/fill_level
    ↓
use ROS header.stamp
    ↓
build front_narrow timestamp index
    ↓
build front_wide timestamp index
    ↓
for each GT:
    nearest narrow
    nearest wide
    ↓
apply <= 1 second GT-camera rule
    ↓
extract JPEG pair
    ↓
write metadata
    ↓
manual visual QC
    ↓
clean manifest

One synchronized sample therefore corresponds to:
one fill-level event
+
one narrow image
+
one wide image

16. Why Many Samples Can Have the Same Fill Level
A numerical fill value is not the same thing as a unique sample.
For example:
10:00:00 → 63%
10:00:01 → 63%
10:00:02 → 63%
10:00:03 → 63%

These are four different timestamped observations.
Each can become a separate sample:
Sample 001 → 63%
Sample 002 → 63%
Sample 003 → 63%
Sample 004 → 63%

The visual appearance may differ even though the rounded ground-truth value remains the same.
However, consecutive samples may also be nearly identical.
Therefore, future analysis should investigate:
temporal redundancy
near-duplicate images
effective visual diversity

A large dataset should represent many meaningful operating states rather than simply many nearly identical consecutive frames.
17. Visual Quality Control
Synchronization alone does not guarantee that a sample is useful.
Examples of invalid samples include:
truck blocks crusher
crusher not visible
camera view obstructed
wrong scene
corrupt image
severe visual obstruction

The project therefore performs manual contact-sheet inspection.
The raw synchronized crusher v3 dataset contained:
5,709 samples

After manual visual QC:
Rejected: 308
Retained: 5,401

Two complete recordings were rejected:
REC 121
REC 384

because truck obstruction was present throughout the relevant recording.
Additional individual samples were rejected from several otherwise usable recordings.
18. Dataset Preservation Strategy
Original synchronized data is not physically deleted.
Instead:
master_metadata.csv

preserves all synchronized samples.
The manually filtered version is stored as:
master_metadata_clean.csv

Rejected samples are recorded in:
rejected_samples.csv

This gives a reversible and auditable data-cleaning process.
19. Incremental Data Acquisition
New MCAPs should not require rebuilding the complete existing dataset.
Instead:
NEW MCAP BATCH
       ↓
day/night classification
       ↓
fill-distribution scan
       ↓
synchronization
       ↓
image extraction
       ↓
manual QC
       ↓
week/session assignment
       ↓
append clean samples

The existing 5,401 samples remain unchanged.
Future batches can be stored independently:
new_batches/
    week_05/
    week_06/
    week_07/

and later merged into a combined clean manifest.
20. Day and Night Domains
Lighting condition is treated as an important domain variable.
Known daylight and night recordings are maintained separately.
The current primary crusher dataset is:
DAY / normal lighting

Night data is maintained separately for domain-generalization experiments.
The intended evaluation can eventually include:
Test 1:
unseen daylight

Test 2:
mixed daylight + night

Test 3:
unseen night only

This allows evaluation of whether a model trained primarily on daylight learns:
actual fill-level geometry

or merely exploits:
lighting-specific visual patterns

21. Zero-Shot VLM Evaluation
Before fine-tuning, several VLM families have been evaluated zero-shot on the crusher task.
The general zero-shot protocol uses:
2 images/sample
temperature = 0
reasoning disabled where possible
strict percentage-only output

Example prompt:
Estimate the fill level of the industrial crusher shown in the two images.
Use visual information from both images.
The fill level is a percentage from 0 to 100,
where 0 means completely empty and 100 means completely full.
Return only the estimated percentage.

Important evaluation metrics include:
MAE
Median Absolute Error
RMSE
Valid-output rate
Bin-wise MAE
prediction distribution
cost
tokens
model ID
raw response

22. Important Zero-Shot Observation
Several models showed prediction concentration.
For example, instead of producing a rich continuous range:
21
36
42
63
74
81
...

a model may repeatedly predict only a small number of values such as:
40
40
40
45
40
35
...

This suggests that zero-shot VLMs may recognize coarse visual states but lack precise numerical calibration for this industrial domain.
This motivates domain-specific fine-tuning.
23. Fine-Tuning Direction
One current candidate is an open multimodal Qwen-family model.
The intended training strategy is likely:
Vision-Language Model
+
LoRA / QLoRA
+
PyTorch
+
CUDA

Full training has deliberately not started yet because the dataset is still being expanded.
The priority remains:
high-quality data
before model optimization

24. Tensors in the Training Pipeline
The persistent dataset currently contains:
JPEG
+
CSV

not pre-generated tensors.
During training:
JPEG
   ↓
image decoder
   ↓
VLM processor
   ↓
pixel tensor
   ↓
GPU
   ↓
vision encoder
   ↓
visual embeddings
   ↓
language model

A conceptual RGB tensor may have shape:
[C, H, W]

for example:
[3, 448, 448]

depending on the selected model.
For multiple images and batches, the processor may internally represent data conceptually as:
[batch, images, channels, height, width]

although the exact format depends on the selected VLM implementation.
25. Text Representation
The textual prompt is also converted into numbers.
For example:
"Estimate the crusher fill level"

is tokenized into token IDs.
Conceptually:
text
 ↓
tokenizer
 ↓
input_ids tensor
 ↓
language model

During generative fine-tuning, the target:
63%

is also represented using language-model tokens.
Therefore the multimodal system combines:
image tensors
+
text-token tensors

inside one model.
26. Multi-Task Training Representation
A future unified multi-task training dataset could use records such as:
{
  "task": "crusher_fill_level",
  "images": [
    "front_narrow.jpg",
    "front_wide.jpg"
  ],
  "prompt": "Estimate the exact crusher fill level from 0 to 100 percent.",
  "target": "63%"
}

{
  "task": "shovel_fill_level",
  "images": [
    "shovel_camera.jpg"
  ],
  "prompt": "Estimate the exact shovel fill level from 0 to 100 percent.",
  "target": "74%"
}

{
  "task": "pile_fill_level",
  "images": [
    "pile_camera.jpg"
  ],
  "prompt": "Estimate the amount of material in the pile from 0 to 100 percent.",
  "target": "46%"
}

{
  "task": "dumping_area_fill",
  "images": [
    "dumping_zone_camera.jpg"
  ],
  "prompt": "Estimate the fill state of the dumping area from 0 to 100 percent.",
  "target": "57%"
}

27. Potential Multi-Task Model Strategies
Several training approaches can eventually be compared.
Strategy A — One Model Per Task
Crusher model
Shovel model
Pile model
Dumping model

This provides a simple task-specific baseline.
Strategy B — One Shared Multi-Task Model
task instruction
+
images
       ↓
shared VLM
       ↓
percentage

Strategy C — Sequential Multi-Task Training
Train initially on the task with the largest/highest-quality dataset, then progressively add additional tasks.
For example:
Crusher
   ↓
Crusher + Shovel
   ↓
Crusher + Shovel + Pile
   ↓
All tasks

Strategy D — Multi-Task LoRA Adapters
A shared base model may use:
shared VLM
+
task-specific adapters

This can later be investigated if one fully shared model suffers from task interference.
28. Important Research Questions
The thesis can investigate questions such as:
RQ1
Can a VLM accurately estimate continuous industrial fill levels from camera imagery?
RQ2
Does domain-specific fine-tuning significantly improve performance over zero-shot VLMs?
RQ3
Can one VLM learn several related material-quantity estimation tasks simultaneously?
RQ4
Does multi-task learning improve or degrade performance relative to independently trained task-specific models?
RQ5
How well does the model generalize to unseen operating sessions?
RQ6
How robust is the model to illumination changes such as daylight versus night operation?
RQ7
How does model accuracy vary across the 0–100% target range?
RQ8
Does training-data imbalance cause systematic prediction bias?
RQ9
How much temporal redundancy exists in continuously recorded industrial datasets?
RQ10
How sensitive is performance to synchronization quality between multiple camera views and ground-truth timestamps?
29. Evaluation Metrics
For continuous percentage prediction, primary metrics should include:
Mean Absolute Error (MAE)
Median Absolute Error
Root Mean Squared Error (RMSE)

Example:
GT         = 63%
Prediction = 58%

Absolute Error = 5 percentage points

Bin-wise evaluation should also be used.
For example:
0–10%
11–20%
21–30%
...
91–100%

This prevents good performance on dominant high-fill ranges from hiding poor performance on underrepresented low-fill cases.
30. Multi-Task Evaluation
The final model should not only have one overall metric.
Results should be reported individually:
Crusher MAE
Shovel MAE
Pile MAE
Dumping-area MAE

and potentially:
overall multi-task MAE

This allows identification of:
easy tasks
difficult tasks
negative transfer
positive transfer

31. Possible Multi-Task Generalization Experiment
A particularly interesting thesis experiment could compare:
Model A:
trained only on crusher

Model B:
trained only on shovel

Model C:
trained on crusher + shovel + pile + dumping

Then compare whether Model C obtains better representations because related tasks reinforce each other.
Possible outcome:
Multi-task improves all tasks

or:
Multi-task improves low-data tasks
but slightly reduces crusher accuracy

Either result would be scientifically meaningful.
32. Dataset Bias and Limitations
Potential sources of bias include:
fill-level imbalance
lighting imbalance
repeated operating cycles
similar camera viewpoints
near-duplicate consecutive frames
different material types
machine position
truck obstruction
session-specific environmental conditions

These should be monitored rather than assuming that sample count alone represents dataset diversity.
33. Ground-Truth Considerations
Ground truth quality is critical.
For the crusher task, the currently used target is:
/processing/crusher/fill_level

from an existing LiDAR-based processing pipeline.
For future tasks such as:
shovel fill
pile quantity
dumping-area fill

the exact labeling source and interpretation must be documented.
The company has automatic labeling infrastructure under development, but every target needs a clear physical definition before being used for model training.
A percentage should not merely be visually convenient; it must correspond to a consistent reference.
34. Project Directory Structure
Current documentation structure:
/workspace/Documentation/

├── 00_Project_Overview/
│   ├── README.md
│   ├── current_status.md
│   └── project_timeline.md
│
├── 01_Dataset/
│   ├── dataset_versions.md
│   ├── dataset_pipeline.md
│   ├── dataset_status.md
│   ├── fill_level_distribution.md
│   ├── qc_notes.md
│   ├── synchronization_analysis.md
│   └── mcap_dataset_inventory.csv
│
├── 02_Zero_Shot_Evaluation/
│   ├── bjarne_model_selection.md
│   ├── evaluation_protocol.md
│   ├── zero_shot_results.md
│   ├── prediction_concentration.md
│   ├── normal_vs_night.md
│   └── cost_tracking.md
│
├── 03_Training_Finetuning/
│   ├── model_selection.md
│   ├── training_plan.md
│   ├── generalization_plan.md
│   └── gpu_plan.md
│
├── 04_Experiments/
│   ├── experiment_log.md
│   └── reproducibility_notes.md
│
└── 05_Meetings_Decisions/
    ├── bjarne_discussions.md
    └── decision_register.md

Operational data remains outside the documentation folder:
/workspace/data
/workspace/extracted
/workspace/scripts
/workspace/results

35. Important Current Files
Crusher dataset:
/workspace/extracted/crusher_dataset_v3/master_metadata.csv
/workspace/extracted/crusher_dataset_v3/master_metadata_clean.csv
/workspace/extracted/crusher_dataset_v3/rejected_samples.csv

Final clean daylight crusher dataset:
5,401 paired samples

Current extraction/QC scripts include:
export_normal_crusher_dataset_v3.py
filter_truck_obstructions_v3.py
create_v3_qc_overview.py
create_v3_full_contact_sheets.py

Zero-shot benchmarking scripts include:
run_openrouter_benchmark.py
run_openrouter_night_benchmark.py

36. Current Project Phase
Current phase:
DATASET EXPANSION

Completed:
✓ crusher task definition
✓ initial dataset extraction
✓ timestamp synchronization
✓ dual-camera pairing
✓ day/night separation
✓ visual QC pipeline
✓ full manual QC of v3
✓ zero-shot VLM benchmarking
✓ prediction-concentration analysis
✓ normal-vs-night evaluation

Current clean crusher dataset:
5,401 samples

Not yet finalized:
train split
validation split
test split
fine-tuning

These are intentionally deferred while the dataset continues to grow.
37. Immediate Next Milestone
Continue collecting new MCAPs.
For every new batch:
MCAP
 ↓
identify lighting domain
 ↓
scan fill distribution
 ↓
extract/synchronize
 ↓
visual QC
 ↓
assign week/session provenance
 ↓
append clean samples
 ↓
update bin coverage

Continue until the data-coverage target is approximately satisfied:
>=10,000 clean crusher samples

with approximately:
>=1,000 samples per 10% interval

subject to actual data availability and visual diversity.
38. After Dataset Collection
Once sufficient data exists:
finalize week/session mapping
        ↓
freeze train / validation / test
        ↓
establish zero-shot baseline
        ↓
fine-tune selected open VLM
        ↓
evaluate normal-domain generalization
        ↓
evaluate night-domain generalization
        ↓
add additional tasks
        ↓
perform multi-task training
        ↓
compare single-task vs multi-task models

39. Expected Thesis Contribution
The intended contribution is broader than simply building a crusher-fill predictor.
The project aims to establish a reproducible framework for:
camera data
+
industrial automatic labels
+
multi-view synchronization
+
data-quality control
+
VLM fine-tuning
+
multi-task visual quantity estimation

for heavy machinery.
A successful outcome would demonstrate that a single multimodal foundation model can be adapted to several related industrial perception tasks using a shared natural-language interface.
Even if full multi-task learning does not outperform specialized models, understanding where and why it succeeds or fails remains a valuable thesis result.
40. Long-Term System Concept
The final conceptual system is:
                    INDUSTRIAL CAMERA DATA
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
      Narrow camera      Wide camera     Other cameras
           │                 │                 │
           └─────────────────┼─────────────────┘
                             │
                             ▼
                    Vision-Language Model
                             │
                       Task instruction
                             │
       ┌─────────────────────┼─────────────────────┐
       │                     │                     │
       ▼                     ▼                     ▼
 Crusher Fill         Shovel Fill            Pile Quantity
    63%                   78%                     42%
                                                   │
                                                   ▼
                                         Dumping Area Fill
                                                57%

The ultimate research goal is therefore:
One visual-language perception framework capable of understanding multiple material-handling states in autonomous heavy-machinery environments and expressing those states as interpretable continuous percentage estimates.


One important distinction in this README is intentional: **crusher fill is documented as the mature, implemented dataset pipeline**, while shovel, pile, and dumping/unloading estimation are described as the broader multi-task thesis scope whose labeling definitions and datasets still need to be finalized. That keeps the README technically honest while showing the full intended direction of the thesis.
