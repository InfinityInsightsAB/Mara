# BGK 12-date same-path step sweep summary for strikes 110, 100, 90, 80, 70 at 20,000 paths

This note records the smaller matched-path rerun with 20,000 direct paths for both LSMC and Hybrid LSMC-PDE.
The fixed benchmark references are still the saved 1200-step runs, and the Euler steps tested here are 24, 48, 72, and 96.

## Winner table

| Scenario | K | Euler steps | LSMC direct error | Hybrid direct error | LSMC SE | Hybrid SE | LSMC CI width | Hybrid CI width | LSMC runtime | Hybrid runtime | Better method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ITM put | 110 | 24 | 2.570% | 1.468% | 0.134578 | 0.0448097677604197 | 0.52754576 | 0.175654289620845 | 1.17 s | 76.83 s | Hybrid |
| ITM put | 110 | 48 | 1.221% | 0.228% | 0.135565 | 0.04551600604325 | 0.5314148 | 0.17842274368954 | 0.46 s | 76.35 s | Hybrid |
| ITM put | 110 | 72 | 0.773% | 0.163% | 0.134824 | 0.045393251472475 | 0.52851008 | 0.177941545772102 | 0.43 s | 76.22 s | Hybrid |
| ITM put | 110 | 96 | 0.561% | 0.407% | 0.136608 | 0.045519890356825 | 0.53550336 | 0.178437970198754 | 0.60 s | 76.91 s | Hybrid |
| ATM | 100 | 24 | 4.025% | 2.001% | 0.118495 | 0.0352303056430969 | 0.4645004 | 0.13810279812094 | 0.35 s | 80.88 s | Hybrid |
| ATM | 100 | 48 | 1.336% | 0.052% | 0.11929 | 0.0359109708156649 | 0.4676168 | 0.140771005597407 | 0.45 s | 80.39 s | Hybrid |
| ATM | 100 | 72 | 0.948% | 0.475% | 0.11743 | 0.0359094617783289 | 0.4603256 | 0.140765090171049 | 0.46 s | 78.05 s | Hybrid |
| ATM | 100 | 96 | 1.694% | 0.172% | 0.119243 | 0.0359982731250466 | 0.46743256 | 0.141113230650183 | 0.53 s | 78.38 s | Hybrid |
| OTM put | 90 | 24 | 5.623% | 3.118% | 0.100936 | 0.0260343691683 | 0.39566912 | 0.102054727139736 | 0.31 s | 81.19 s | Hybrid |
| OTM put | 90 | 48 | 2.173% | 0.248% | 0.098998 | 0.026580401019062 | 0.38807216 | 0.104195171994723 | 0.49 s | 82.72 s | Hybrid |
| OTM put | 90 | 72 | 1.788% | 0.418% | 0.098666 | 0.0266741866450021 | 0.38677072 | 0.104562811648408 | 0.50 s | 78.74 s | Hybrid |
| OTM put | 90 | 96 | 1.994% | 0.253% | 0.098457 | 0.0267214061575337 | 0.38595144 | 0.104747912137532 | 0.54 s | 78.47 s | Hybrid |
| K=80 put | 80 | 24 | 7.445% | 4.810% | 0.080613 | 0.0181181348700546 | 0.31600296 | 0.071023088690614 | 0.38 s | 81.11 s | Hybrid |
| K=80 put | 80 | 48 | 3.193% | 0.832% | 0.077914 | 0.0184967185443028 | 0.30542288 | 0.0725071366936668 | 0.45 s | 79.17 s | Hybrid |
| K=80 put | 80 | 72 | 1.645% | 0.012% | 0.076738 | 0.0186450835974411 | 0.30081296 | 0.0730887277019692 | 0.49 s | 78.68 s | Hybrid |
| K=80 put | 80 | 96 | 1.742% | 0.668% | 0.076453 | 0.0186249799228231 | 0.29969576 | 0.0730099212974665 | 0.62 s | 78.89 s | Hybrid |
| K=70 put | 70 | 24 | 8.911% | 6.757% | 0.061172 | 0.011821808641478 | 0.23979424 | 0.0463414898745938 | 0.35 s | 81.71 s | Hybrid |
| K=70 put | 70 | 48 | 3.890% | 1.589% | 0.059206 | 0.0120694715134655 | 0.23208752 | 0.0473123283327846 | 0.43 s | 78.10 s | Hybrid |
| K=70 put | 70 | 72 | 1.476% | 0.560% | 0.057802 | 0.0122057571315721 | 0.22658384 | 0.0478465679557625 | 0.50 s | 78.67 s | Hybrid |
| K=70 put | 70 | 96 | 0.748% | 1.186% | 0.058068 | 0.0121237436028833 | 0.22762656 | 0.0475250749233024 | 0.57 s | 78.37 s | LSMC |

## Hybrid win counts

| Scenario | Hybrid better at steps |
| --- | --- |
| ITM put | 24, 48, 72, 96 |
| ATM | 24, 48, 72, 96 |
| OTM put | 24, 48, 72, 96 |
| K=80 put | 24, 48, 72, 96 |
| K=70 put | 24, 48, 72 |

## Main takeaway

- Reducing the matched path budget from 60,000 to 20,000 widens the intervals for both methods and increases direct error for both methods.
- The Hybrid advantage usually becomes clearer, because the benchmark deteriorates faster while Hybrid retains much smaller SE and CI width.
- In this 20,000-path rerun, Hybrid is better at all four steps for ATM, OTM, and K=80, at all four steps for ITM, and at three of the four steps for K=70.
