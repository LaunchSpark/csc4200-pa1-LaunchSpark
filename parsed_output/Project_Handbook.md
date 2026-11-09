## CSC 4200/5200 Computer Networks

## Project Handbook

PA1, PA2 and the Final Project: one network stack, built in three steps

Fall 2026 · Tennessee Tech University, Department of Computer Science · Dr. Eric L. Brown

| At a Glance   |                                                                                                                                              |
|---------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| What          | A file-transfer service, built twice - once over TCP and once over a trans- port you build yourself on UDP - and then joined into one stack. |
| Pieces        | PA1 (individual), PA2 (individual), Final Project (pairs).                                                                                   |
| Read          | After the midterm: this handbook, the ETP/1 Specification, and the PA1 brief.                                                                |
| PA1 due       | Friday 6 November, 11:59 pm Central.                                                                                                         |
| Project due   | Code Friday 4 December, 11:59 pm; report and video Tuesday 8 December, 12:30 pm.                                                             |
| Kit           | ~/csc4200-course/project/ after git pull: starter code and the self- check tool.                                                             |

## Contents

| 1   | The Big Picture              | . . . . . . . . . . . . . . . . . . . . . . . . . .         | . . . . . . . . . . . . . . . . . 1   |
|-----|------------------------------|-------------------------------------------------------------|---------------------------------------|
| 2   | Calendar                     | . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . | . . . . . . . . . . . . . . . . . 3   |
| 3   | The Three Milestones         | . . . . . . . . . . . . . . . . . . . . . . .               | . . . . . . . . . . . . . . . . . 4   |
|     | 3.1                          | PA1 (now) . . . . . . . . . . . . . . . . . . . . . . . . . | . . . . . . . . . . . . . . . . . 4   |
|     | 3.2                          | PA2 (posted 3 November) . . . . . . . . . . . . . . . .     | . . . . . . . . . . . . . . . . . 4   |
|     | 3.3                          | The Final Project (brief posted 10 November) . . . . .      | . . . . . . . . . . . . . . . . . 4   |
| 4   | Working Alone, Then in Pairs | . . . . . . . . . . . . . . . . . .                         | . . . . . . . . . . . . . . . . . 5   |
| 5   | Tools You Will Use           | . . . . . . . . . . . . . . . . . . . . . . . .             | . . . . . . . . . . . . . . . . . 5   |
| 6   | AI, Authorship and You       | . . . . . . . . . . . . . . . . . . . . .                   | . . . . . . . . . . . . . . . . . 6   |
| 7   | Submitting and Grading       | . . . . . . . . . . . . . . . . . . . . .                   | . . . . . . . . . . . . . . . . . 7   |
| 8   | Getting Help .               | . . . . . . . . . . . . . . . . . . . . . . . . . . .       | . . . . . . . . . . . . . . . . . 8   |

## 1 The Big Picture

For the rest of the term you will build one thing in three steps: a small file-transfer service, the Eagle Transfer Protocol (ETP), and the network stack underneath it.

PA1 - the application over TCP. You implement the ETP/1 server and client from a written specification, the way real protocols are implemented: from an RFC. Your server serves many clients at once and survives the ones that misbehave. Then you capture your own session on the wire and explain, segment by segment, what TCP did with your bytes.

Figure 1. Three milestones. The project joins PA1's application to PA2's transport through the seam that PA1 requires.

<!-- image -->

- PA2 - a reliable transport over UDP. UDP loses, duplicates and reorders. You build ETP-T, a small reliable byte stream on top of it - sequence numbers, acknowledgments, a checksum, a retransmission timer and a sliding window - and you measure it through a relay that drops, delays and reorders your datagrams.
- The Final Project - your stack, end to end. With a partner, you put the PA1 application on top of the PA2 transport, add one extension, and measure the result against TCP under the same conditions. You report what you found in writing and in a short video.

The hinge is the transport seam (ETP/1 Specification, Section 11). In PA1 your code may touch the network only through six small functions. If you keep that rule, the project's big switch - TCP out, your own transport in - is an afternoon. If you don't, it is a rewrite. Keep the rule.

## What This Work Evidences

ACM CS2023: NC-Applications, "Implement a simple client-server socket-based application" (PA1); NC-Reliability, "Design and implement a simple reliable protocol" (PA2 and the project). NCAE-C CAE-CD: BNW-3, tracking and identifying the packets in a simple TCP connection (PA1's capture analysis). Course outcome [CIO 4]: design, implement, and document a networked client-server application using a defined protocol, and interpret the evidence its operation produces.

## 2 Calendar

Five working weeks, with Thanksgiving week left free. All times are Central.

Table 1. Project calendar, Fall 2026.

| When                                                                                                                                                                                                                                                                 | What                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Tue 20 Oct Thu 22 Oct Week 1 26-30 Oct Week 2 2-6 Nov Tue 3 Nov Fri 6 Nov 11:59 pm Week 3 9-13 Nov Tue 10 Nov Fri 13 Nov 11:59 pm Week 4 16-20 Nov Mon 16 Nov Fri 20 Nov 11:59 pm 23-27 Nov Thanksgiving Week 5 30 Nov - 4 Dec Fri 4 Dec 11:59 pm Tue 8 Dec 12:30 pm | Handbook, ETP/1 Specification and PA1 brief posted. Read them after the midterm. Midterm. PA1 under way. In class: the specification, the seam, framing. PA2 brief, ETP-T specification and the lossy relay posted. PA1 due. Final Project brief posted: rubric, extension menu, report and video require- ments. Pairs declared in Canvas (People → Project Pairs). Anyone without a partner is paired by the instructor. PA2 due. break: no deadlines, no milestones Integration, extension and measurement. No class presentations: the video replaces them. Project code freeze (last day of classes). Project report and video due (finals week). |

## Practitioner Note: Why the deadlines fall where they do

PA1 is due before PA2 gets hard, and graded feedback on PA1 comes back about a week later - before PA2 is due. PA2 does not depend on your PA1 code, so a rough PA1 does not stall PA2. Thanksgiving week is yours. Code freezes on the last day of class so that the report and video describe a fixed, graded commit.

## 3 The Three Milestones

| Milestone     | Who        | Grade category   | You hand in                                                           |
|---------------|------------|------------------|-----------------------------------------------------------------------|
| PA1           | individual | Assignments      | a repository: server, client, capture, analysis, design, disclosure   |
| PA2           | individual | Assignments      | a repository: ETP-T, measurements, analysis, design, disclosure       |
| Final Project | pairs      | Project          | a repository at the code freeze; a written report; a 5-7 minute video |

## 3.1 PA1 (now)

Everything is in the PA1 brief. Each PA is scored out of 100, in three parts: execution (30, automatic: the same tests you can run yourself), evidence and interpretation (30: your capture and what you make of it), and engineering and documentation (40: build, repository practice, design and disclosure).

## 3.2 PA2 (posted 3 November)

ETP-T carries a byte stream over UDP with sequence numbers, cumulative acknowledgments, an Internet checksum (Chapter 5, §5.3.2), a retransmission timer and a sliding window (§5.4). You will run it through an instructor-supplied lossy relay - a small program that sits between your sender and receiver and drops, delays and reorders datagrams - using a random seed assigned to you, and measure throughput against window size and loss rate, comparing it with the stop-and-wait bound.

## 3.3 The Final Project (brief posted 10 November)

With your partner you put the ETP/1 application on ETP-T through the seam, choose one extension, and measure your stack against TCP under identical relay conditions. The extension menu will include Go-Back-N versus Selective Repeat, AIMD congestion control, a connection handshake and teardown, a multi-client server over ETP-T, and confidentiality and integrity with authenticated encryption (AES-GCM).

The three project components are weighted as follows within the Project category.

| Component                                                     | Due                 | Share of the Project grade   |
|---------------------------------------------------------------|---------------------|------------------------------|
| Implementation                                                | Fri 4 Dec, 11:59 pm | 40%                          |
| Written report                                                | Tue 8 Dec, 12:30 pm | 35%                          |
| Video (5-7 minutes, both partners speak, includes a live run) | Tue 8 Dec, 12:30 pm | 25%                          |

CSC 5200 students do the same project work as everyone else. Graduate differentiation is the additional research paper described in the syllabus, valued within the Project category (which is why that category weighs 20% for CSC 5200 rather than 15%); there is no extra coding requirement. The Final Project brief states how the category divides between the paper and the three components above.

## 4 Working Alone, Then in Pairs

PA1 and PA2 are individual. Talk about ideas with anyone; write your own code, capture and analysis. Sharing code, captures or answers is not allowed.

The Final Project is done in pairs:

- Join a group in Canvas (People → Project Pairs) by Friday 13 November. Anyone not in a pair on Monday 16 November is paired by the instructor. With an odd class size, one group will be a trio, and the trio takes on a second extension.
- CSC 4200 and CSC 5200 students may pair with each other.
- Your project may start from either partner's PA1 and PA2, or a blend. Choose the best parts; say in the report whose they were.
- Both partners commit to the shared repository. The report includes a short contribution statement signed by both. If the commit history and the statement show a very uneven split, individual project grades may differ.

## 5 Tools You Will Use

- Your Lab 0 virtual machine. All building, running, capturing and testing happen there (or on your own host). It is your authorised scope.
- The course kit. cd ~/csc4200-course &amp;&amp; git pull brings down project/: the starter code in C and in Python, and etp\_selfcheck.py. The self-check runs the same execution tests the grader runs, and scores your build and repository by the same rules. Run it early and often. The only scores it cannot show you are the ones people judge, and whether your capture facts are right.
- Your own private GitHub repositories, one per milestone, with the instructor and the GTA added as collaborators. You submit by pasting the repository URL and a commit SHA into Canvas; that commit is what is graded.
- Wireshark, tshark, tcpdump and ss for watching your traffic and your sockets.
- The lossy relay (from PA2 on), for making a perfect loopback behave like a bad network, reproducibly.

## 6 AI, Authorship and You

This section applies to every milestone. Each brief names that milestone's core. For packet captures and measurements in this project, this section replaces the syllabus's "tool syntax only" rule for packet-analysis write-ups.

You may use generative AI tools in this project. Working engineers do, and learning to use them well is part of what this course should teach you. But the point of these assignments is that you learn network programming: how a byte stream behaves, how framing works, how a server survives its clients, how reliability is built from loss. A tool that does that thinking for you takes the learning with it, and the final exam, the project, and your first job will find the gap.

## Encouraged (disclose it)

- Explaining a concept, an error message, a manual page, or a passage of the specification.
- Reviewing code you wrote: finding bugs, questioning unclear parts, pointing at the specification rule you broke.
- Helping you design tests and think of edge cases.
- Tooling: make, git, argument parsing, shell commands, Wireshark display filters.
- Helping you understand what you are looking at in a capture - what a field means, why TIME-WAIT exists, why segment sizes vary - and editing your prose for clarity. The ideas, the numbers and the reasoning stay yours.

## Not allowed

- the code each brief names as the core of that milestone - for PA1, the framing, the transport seam and the server's session handling.
 The values come from your own capture and the reasoning is in your own words.

## Always

- Disclose every use in AI\_USE.md: what you asked, what you used, what you changed, how you checked it, and one thing the tool got wrong - or, if you found nothing wrong, how you checked.
- Be able to explain every line you submit. Code you cannot explain is not your work, whoever typed it.
- Sign the authorship statement at the end of your README.md.

## The explanation conversation

Any student may be asked to meet with the instructor or the GTA for about ten minutes to walk through their submission: explain a function, make a small change, read a line of their capture. Some students are chosen at random; others because something in a submission needs a conversation. Being asked is not an accusation. A part of the work you cannot explain earns no credit, and a pattern of that is handled under TNTech Policy 216 (Academic Integrity).



 The instructor welcomes your help as a tutor, reviewer and debugging partner, and asks that you not act as the author.

Please do: explain concepts, the specification, the socket API, error messages and Wireshark; review and critique code the student has written, and ask questions that lead them to find and fix their own bugs; help them design tests; help with tooling such as make, git and the shell.

Please do not: write the core code each assignment brief reserves for the student (listed under Not allowed), in whole or in large part; write answers to the analysis questions; read the student's capture and report the values to fill in; or complete the assignment end to end.

If you are asked to do one of those things, please say that the course asks you not to, and offer to work through it with the student one step at a time instead. Thank you.

To the student: this note is here in the open, on purpose. 

## 7 Submitting and Grading

1. Push your work to your private repository.
2. In Canvas, submit a text entry with two things: the repository URL and the full 40-character commit SHA (git rev-parse HEAD).
3. That commit is what is graded. Pushing afterwards changes nothing unless you submit a new SHA, and a new SHA after the deadline is late work under the syllabus.

Grading is designed so that nothing surprises you. The execution, build and repository scores are computed by the same code the self-check runs. The capture facts are compared with your own capture. Everything people score - your interpretation, design and documentation - is scored on the bands printed in the brief. Feedback comes back as a Canvas comment listing each part and why.

Deadlines and late work follow the syllabus. If a deadline is going to be a problem, talk to me before it passes, not after.

## 8 Getting Help

- Specification questions: the Canvas discussion ETP Specification Questions. If you wondered, someone else did too. Answers that change or clarify a rule go into the specification's change log.
- Stuck on a bug for more than an hour? Come to office hours or ask the GTA. Bring the self-check output and what you have already tried.
- Budget your time. Plan on roughly 6-8 hours a week outside class for the next five working weeks. Start PA1 the week of 26 October, not the week of 2 November.

## Authorised Scope

Everything you build here runs on loopback or inside your Lab 0 virtual machine. Capture only your own loopback traffic. Do not point your client, your server, the relay or a capture at any other host or network. The syllabus's Hands-On Activity Scope and Authorization rules apply in full. Use synthetic data - random bytes or files you made - never real credentials or personal data.