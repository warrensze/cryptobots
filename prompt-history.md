# Prompt History

This document records the user's prompts from the datalogging planning conversation so the work can be resumed later.

## Prompt 1

```text
review the current project cakled superpowered2022.  As part of the main,py file and this youtube video https://www.youtube.com/watch?v=YvdNfw3_fhA, I would like to do the same thing the FLL team is doing with creating a datalogging program.  But we don't want to use pybricks.  We do have SPike Prime kit and Visual Studio Code.  Plan out how to do this with basic Lego Spike Prime and MicroPython.
```

## Prompt 2

```text
is there a way to create our own DataLog object/functionality using micropython?
```

## Prompt 3

```text
Can you also make it more convenient to collect the data so that we can just easily collect the generated data without having to watch the console?
```

## Prompt 4

```text
Planning only right now
```

## Prompt 5

```text
Is there a way to only involve the computer at the end when downloading the data?
```

## Prompt 6

```text
use the folder called cryptobots.  doument this plan there.  Also, in case I lose this session, document the context in a concise manner so that we could pick things up if we lose contact.  Also in another separate doc, document my prompts.  All of this should be in the folder called cryptobots
```

## Prompt 7

```text
Proceed with the plan.  Put all the code in cryptobots folder in a subfolder for the code.  We will leave the original code untouched
```

## Prompt 8

```text
for now, I only need to do the datalogging, where a user can press a button to start data collection, move the robot manually, the gryo will sense the changes and log the data, then press a button to stop collecting data.  then the user can plug the robot to the computer and download the data.  Provide simple step by step instructions to do this with the new code OR update the code so that we can do this.  All of this is in cryptobots folder
```

## Prompt 9

```text
you need to adjust the code.  we can only upload 1 program to the hub
```

## Prompt 10

```text
i'd like to check in the cryptobots folder in to a new github repo.  can you help me with that
```

## Prompt 11

```text
Disconnect the project from the original repo.  I don't want to accidently write to that repo
```

## Prompt 12

```text
update the docs with any latest changes or context
```

## Prompt 13

```text
The folders have moved around a little.  There is a cryptobots folder and superpower folder.  The current scripts we made for datalogging isn't working quite right.  Review the datalogging code under superpower.  Analyze our scripts under cryptobots.  Plan out again a script to mimic the datalogging code exactly using micropython
```

## Prompt 14

```text
the datalogging we need is only time, distance and gyroangle.  You can leave off the other metrics.
```

## Prompt 15

```text
Here is an example of what the original DataLogger output.  We want the exact same format.  A nice csv that we can use
```

## Prompt 16

```text
Examine the original DataLogger code and see what units their time is in.
```

## Prompt 17

```text
Is our DataLogging tracking data at the same frequency as the original?  When we were using it before we were expecting more data points
```

## Prompt 18

```text
we need to be the same or as close to the original as possible
```

## Prompt 19

```text
we need denser.  The route is usually only 2-3 seconds long anyways.  Make it as dense as the original
```

## Prompt 20

```text
how do we get the data off of the hub?  Is it as easy as it can be?
```

## Prompt 21

```text
it will already be connected using a vs code extension
```

## Prompt 22

```text
will this code work without using a separate vs code extension?
```

## Prompt 23

```text
we are only doing 1 run at a time.  Make it cleaner so that we can just copy and paste
```

## Notes

The current implementation focus is one-run-at-a-time manual drive datalogging on SPIKE Prime using stock LEGO MicroPython. The hub prints plain CSV directly to the VS Code console with columns `time,distance,gyro_angle`.
