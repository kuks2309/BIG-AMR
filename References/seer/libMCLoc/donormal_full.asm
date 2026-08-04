
/media/amap/6ab6980d-f090-4387-8753-a2251e75651d/usr/local/SeerRobotics/rbk/plugins/libMCLoc.so:     file format elf64-x86-64


Disassembly of section .text:

00000000003ca440 <_ZN5MCLoc20DoNormalUpdateActionEv>:
  3ca440:	55                   	push   %rbp
  3ca441:	48 89 e5             	mov    %rsp,%rbp
  3ca444:	41 57                	push   %r15
  3ca446:	41 56                	push   %r14
  3ca448:	41 55                	push   %r13
  3ca44a:	41 54                	push   %r12
  3ca44c:	53                   	push   %rbx
  3ca44d:	48 83 e4 f0          	and    $0xfffffffffffffff0,%rsp
  3ca451:	48 81 ec 30 04 00 00 	sub    $0x430,%rsp
  3ca458:	49 89 ff             	mov    %rdi,%r15
  3ca45b:	48 8d 3d 06 cc 52 00 	lea    0x52cc06(%rip),%rdi        # 8f7068 <.got>
  3ca462:	e8 f9 d8 de ff       	call   1b7d60 <__tls_get_addr@plt>
  3ca467:	48 89 c3             	mov    %rax,%rbx
  3ca46a:	8a 80 e8 00 00 00    	mov    0xe8(%rax),%al
  3ca470:	84 c0                	test   %al,%al
  3ca472:	0f 84 12 37 00 00    	je     3cdb8a <_ZN5MCLoc20DoNormalUpdateActionEv+0x374a>
  3ca478:	48 89 d8             	mov    %rbx,%rax
  3ca47b:	48 8b b0 e0 00 00 00 	mov    0xe0(%rax),%rsi
  3ca482:	48 8d 15 95 08 1f 00 	lea    0x1f0895(%rip),%rdx        # 5bad1e <_ZTSZN3rbk6Logger6Thread11move2threadIZN17QuadGridSearchMap15getPostProbBaseERKNS_9algorithm10StateVar2DERSt6vectorIdSaIdEEiE5$_125JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x22ae>
  3ca489:	48 8d bc 24 f8 02 00 	lea    0x2f8(%rsp),%rdi
  3ca490:	00 
  3ca491:	e8 2a 4d de ff       	call   1af1c0 <_ZN8profiler10ScopedZoneC1EmPKc@plt>
  3ca496:	49 8d 9f f0 0e 00 00 	lea    0xef0(%r15),%rbx
  3ca49d:	48 83 3d 8b f6 52 00 	cmpq   $0x0,0x52f68b(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ca4a4:	00 
  3ca4a5:	74 10                	je     3ca4b7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x77>
  3ca4a7:	48 89 df             	mov    %rbx,%rdi
  3ca4aa:	e8 81 d1 de ff       	call   1b7630 <pthread_mutex_lock@plt>
  3ca4af:	85 c0                	test   %eax,%eax
  3ca4b1:	0f 85 24 37 00 00    	jne    3cdbdb <_ZN5MCLoc20DoNormalUpdateActionEv+0x379b>
  3ca4b7:	f2 41 0f 10 87 50 0f 	movsd  0xf50(%r15),%xmm0
  3ca4be:	00 00 
  3ca4c0:	f2 0f 11 84 24 00 01 	movsd  %xmm0,0x100(%rsp)
  3ca4c7:	00 00 
  3ca4c9:	f2 41 0f 10 87 58 0f 	movsd  0xf58(%r15),%xmm0
  3ca4d0:	00 00 
  3ca4d2:	f2 0f 11 84 24 f0 00 	movsd  %xmm0,0xf0(%rsp)
  3ca4d9:	00 00 
  3ca4db:	f2 41 0f 10 87 60 0f 	movsd  0xf60(%r15),%xmm0
  3ca4e2:	00 00 
  3ca4e4:	f2 0f 11 84 24 c0 00 	movsd  %xmm0,0xc0(%rsp)
  3ca4eb:	00 00 
  3ca4ed:	48 83 3d 3b f6 52 00 	cmpq   $0x0,0x52f63b(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ca4f4:	00 
  3ca4f5:	74 08                	je     3ca4ff <_ZN5MCLoc20DoNormalUpdateActionEv+0xbf>
  3ca4f7:	48 89 df             	mov    %rbx,%rdi
  3ca4fa:	e8 b1 d0 de ff       	call   1b75b0 <pthread_mutex_unlock@plt>
  3ca4ff:	4c 89 ff             	mov    %r15,%rdi
  3ca502:	e8 f9 d3 de ff       	call   1b7900 <_ZN5MCLoc14SetMeasurementEv@plt>
  3ca507:	48 8d bc 24 b8 02 00 	lea    0x2b8(%rsp),%rdi
  3ca50e:	00 
  3ca50f:	e8 fc d5 de ff       	call   1b7b10 <_ZN3rbk9algorithm13MCLParticle2DC1Ev@plt>
  3ca514:	48 8d bc 24 00 04 00 	lea    0x400(%rsp),%rdi
  3ca51b:	00 
  3ca51c:	e8 ef d5 de ff       	call   1b7b10 <_ZN3rbk9algorithm13MCLParticle2DC1Ev@plt>
  3ca521:	48 8d bc 24 00 04 00 	lea    0x400(%rsp),%rdi
  3ca528:	00 
  3ca529:	f2 0f 10 84 24 00 01 	movsd  0x100(%rsp),%xmm0
  3ca530:	00 00 
  3ca532:	f2 0f 10 8c 24 f0 00 	movsd  0xf0(%rsp),%xmm1
  3ca539:	00 00 
  3ca53b:	f2 0f 10 94 24 c0 00 	movsd  0xc0(%rsp),%xmm2
  3ca542:	00 00 
  3ca544:	e8 57 67 de ff       	call   1b0ca0 <_ZN3rbk9algorithm13MCLParticle2D16setParticleValueEddd@plt>
  3ca549:	66 0f 57 c0          	xorpd  %xmm0,%xmm0
  3ca54d:	66 0f 29 84 24 a0 02 	movapd %xmm0,0x2a0(%rsp)
  3ca554:	00 00 
  3ca556:	48 c7 84 24 b0 02 00 	movq   $0x0,0x2b0(%rsp)
  3ca55d:	00 00 00 00 00 
  3ca562:	0f 10 8c 24 00 04 00 	movups 0x400(%rsp),%xmm1
  3ca569:	00 
  3ca56a:	66 0f 10 94 24 10 04 	movupd 0x410(%rsp),%xmm2
  3ca571:	00 00 
  3ca573:	0f 29 8c 24 40 03 00 	movaps %xmm1,0x340(%rsp)
  3ca57a:	00 
  3ca57b:	66 0f 29 94 24 50 03 	movapd %xmm2,0x350(%rsp)
  3ca582:	00 00 
  3ca584:	49 8d bf 68 d0 d0 03 	lea    0x3d0d068(%r15),%rdi
  3ca58b:	48 8b 84 24 20 04 00 	mov    0x420(%rsp),%rax
  3ca592:	00 
  3ca593:	48 89 84 24 60 03 00 	mov    %rax,0x360(%rsp)
  3ca59a:	00 
  3ca59b:	66 0f 29 84 24 00 03 	movapd %xmm0,0x300(%rsp)
  3ca5a2:	00 00 
  3ca5a4:	48 c7 84 24 10 03 00 	movq   $0x0,0x310(%rsp)
  3ca5ab:	00 00 00 00 00 
  3ca5b0:	48 c7 84 24 08 03 00 	movq   $0x0,0x308(%rsp)
  3ca5b7:	00 00 00 00 00 
  3ca5bc:	48 8b 84 24 60 03 00 	mov    0x360(%rsp),%rax
  3ca5c3:	00 
  3ca5c4:	48 89 44 24 20       	mov    %rax,0x20(%rsp)
  3ca5c9:	66 0f 28 84 24 40 03 	movapd 0x340(%rsp),%xmm0
  3ca5d0:	00 00 
  3ca5d2:	66 0f 28 8c 24 50 03 	movapd 0x350(%rsp),%xmm1
  3ca5d9:	00 00 
  3ca5db:	66 0f 11 4c 24 10    	movupd %xmm1,0x10(%rsp)
  3ca5e1:	66 0f 11 04 24       	movupd %xmm0,(%rsp)
  3ca5e6:	48 8d b4 24 00 03 00 	lea    0x300(%rsp),%rsi
  3ca5ed:	00 
  3ca5ee:	48 89 bc 24 f8 00 00 	mov    %rdi,0xf8(%rsp)
  3ca5f5:	00 
  3ca5f6:	e8 15 d3 de ff       	call   1b7910 <_ZN3rbk9algorithm16ParticleFilter2D21getParticleLikelihoodENS0_13MCLParticle2DESt6vectorIdSaIdEE@plt>
  3ca5fb:	f2 0f 11 84 24 10 01 	movsd  %xmm0,0x110(%rsp)
  3ca602:	00 00 
  3ca604:	48 8b bc 24 00 03 00 	mov    0x300(%rsp),%rdi
  3ca60b:	00 
  3ca60c:	48 85 ff             	test   %rdi,%rdi
  3ca60f:	74 05                	je     3ca616 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1d6>
  3ca611:	e8 da 52 de ff       	call   1af8f0 <_ZdlPv@plt>
  3ca616:	48 8d bc 24 b8 02 00 	lea    0x2b8(%rsp),%rdi
  3ca61d:	00 
  3ca61e:	f3 0f 7e 84 24 00 01 	movq   0x100(%rsp),%xmm0
  3ca625:	00 00 
  3ca627:	f3 0f 7e 8c 24 f0 00 	movq   0xf0(%rsp),%xmm1
  3ca62e:	00 00 
  3ca630:	f2 0f 10 94 24 c0 00 	movsd  0xc0(%rsp),%xmm2
  3ca637:	00 00 
  3ca639:	e8 62 66 de ff       	call   1b0ca0 <_ZN3rbk9algorithm13MCLParticle2D16setParticleValueEddd@plt>
  3ca63e:	48 8d bc 24 b8 02 00 	lea    0x2b8(%rsp),%rdi
  3ca645:	00 
  3ca646:	f3 0f 7e 84 24 10 01 	movq   0x110(%rsp),%xmm0
  3ca64d:	00 00 
  3ca64f:	e8 fc 62 de ff       	call   1b0950 <_ZN3rbk9algorithm13MCLParticle2D9setWeightEd@plt>
  3ca654:	49 8b bf a8 d2 d0 03 	mov    0x3d0d2a8(%r15),%rdi
  3ca65b:	48 8d b4 24 18 03 00 	lea    0x318(%rsp),%rsi
  3ca662:	00 
  3ca663:	e8 b8 ce de ff       	call   1b7520 <_ZN3rbk9algorithm16MCLMotionModel2D20getCurrentControlVarERNS0_12ControlVar2DE@plt>
  3ca668:	f2 0f 10 8c 24 18 03 	movsd  0x318(%rsp),%xmm1
  3ca66f:	00 00 
  3ca671:	f2 0f 10 84 24 20 03 	movsd  0x320(%rsp),%xmm0
  3ca678:	00 00 
  3ca67a:	f2 0f 10 94 24 28 03 	movsd  0x328(%rsp),%xmm2
  3ca681:	00 00 
  3ca683:	f2 0f 5c 0d 4d 97 53 	subsd  0x53974d(%rip),%xmm1        # 903dd8 <_ZZN5MCLoc20DoNormalUpdateActionEvE23accumulated_control_var>
  3ca68a:	00 
  3ca68b:	f2 0f 5c 05 4d 97 53 	subsd  0x53974d(%rip),%xmm0        # 903de0 <_ZZN5MCLoc20DoNormalUpdateActionEvE23accumulated_control_var+0x8>
  3ca692:	00 
  3ca693:	f2 0f 5c 15 4d 97 53 	subsd  0x53974d(%rip),%xmm2        # 903de8 <_ZZN5MCLoc20DoNormalUpdateActionEvE23accumulated_control_var+0x10>
  3ca69a:	00 
  3ca69b:	f2 0f 59 c9          	mulsd  %xmm1,%xmm1
  3ca69f:	f2 0f 59 c0          	mulsd  %xmm0,%xmm0
  3ca6a3:	f2 0f 58 c1          	addsd  %xmm1,%xmm0
  3ca6a7:	66 0f 57 c9          	xorpd  %xmm1,%xmm1
  3ca6ab:	66 0f 2e c1          	ucomisd %xmm1,%xmm0
  3ca6af:	72 06                	jb     3ca6b7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x277>
  3ca6b1:	f2 0f 51 c0          	sqrtsd %xmm0,%xmm0
  3ca6b5:	eb 17                	jmp    3ca6ce <_ZN5MCLoc20DoNormalUpdateActionEv+0x28e>
  3ca6b7:	66 0f 29 94 24 00 01 	movapd %xmm2,0x100(%rsp)
  3ca6be:	00 00 
  3ca6c0:	e8 1b 50 de ff       	call   1af6e0 <sqrt@plt>
  3ca6c5:	66 0f 28 94 24 00 01 	movapd 0x100(%rsp),%xmm2
  3ca6cc:	00 00 
  3ca6ce:	f2 0f 11 84 24 f0 00 	movsd  %xmm0,0xf0(%rsp)
  3ca6d5:	00 00 
  3ca6d7:	f2 0f 59 15 99 82 19 	mulsd  0x198299(%rip),%xmm2        # 562978 <_ZTS11errorLogger+0x2e>
  3ca6de:	00 
  3ca6df:	48 8b 05 52 fa 52 00 	mov    0x52fa52(%rip),%rax        # 8fa138 <_ZN3rbk10foundation4math2PIE>
  3ca6e6:	f2 0f 5e 10          	divsd  (%rax),%xmm2
  3ca6ea:	66 0f 29 94 24 00 01 	movapd %xmm2,0x100(%rsp)
  3ca6f1:	00 00 
  3ca6f3:	0f 10 84 24 18 03 00 	movups 0x318(%rsp),%xmm0
  3ca6fa:	00 
  3ca6fb:	0f 10 8c 24 28 03 00 	movups 0x328(%rsp),%xmm1
  3ca702:	00 
  3ca703:	0f 11 05 ce 96 53 00 	movups %xmm0,0x5396ce(%rip)        # 903dd8 <_ZZN5MCLoc20DoNormalUpdateActionEvE23accumulated_control_var>
  3ca70a:	0f 11 0d d7 96 53 00 	movups %xmm1,0x5396d7(%rip)        # 903de8 <_ZZN5MCLoc20DoNormalUpdateActionEvE23accumulated_control_var+0x10>
  3ca711:	48 8b 84 24 38 03 00 	mov    0x338(%rsp),%rax
  3ca718:	00 
  3ca719:	48 89 05 d8 96 53 00 	mov    %rax,0x5396d8(%rip)        # 903df8 <_ZZN5MCLoc20DoNormalUpdateActionEvE23accumulated_control_var+0x20>
  3ca720:	48 b8 00 00 00 00 00 	movabs $0xc058c00000000000,%rax
  3ca727:	c0 58 c0 
  3ca72a:	48 89 84 24 e8 00 00 	mov    %rax,0xe8(%rsp)
  3ca731:	00 
  3ca732:	f3 41 0f 7e 8f e0 19 	movq   0x19e0(%r15),%xmm1
  3ca739:	00 00 
  3ca73b:	66 0f db 0d ad 83 19 	pand   0x1983ad(%rip),%xmm1        # 562af0 <_ZTS11errorLogger+0x1a6>
  3ca742:	00 
  3ca743:	48 8b 05 86 d7 52 00 	mov    0x52d786(%rip),%rax        # 8f7ed0 <_ZN3rbk10foundation4math7EpsilonE>
  3ca74a:	f3 0f 7e 00          	movq   (%rax),%xmm0
  3ca74e:	66 0f 2e c8          	ucomisd %xmm0,%xmm1
  3ca752:	77 1b                	ja     3ca76f <_ZN5MCLoc20DoNormalUpdateActionEv+0x32f>
  3ca754:	f3 41 0f 7e 8f e8 19 	movq   0x19e8(%r15),%xmm1
  3ca75b:	00 00 
  3ca75d:	66 0f db 0d 8b 83 19 	pand   0x19838b(%rip),%xmm1        # 562af0 <_ZTS11errorLogger+0x1a6>
  3ca764:	00 
  3ca765:	66 0f 2e c8          	ucomisd %xmm0,%xmm1
  3ca769:	0f 86 7f 05 00 00    	jbe    3cacee <_ZN5MCLoc20DoNormalUpdateActionEv+0x8ae>
  3ca76f:	48 b8 00 00 00 00 00 	movabs $0x4018000000000000,%rax
  3ca776:	00 18 40 
  3ca779:	48 89 84 24 e8 00 00 	mov    %rax,0xe8(%rsp)
  3ca780:	00 
  3ca781:	41 8a 87 28 0c 00 00 	mov    0xc28(%r15),%al
  3ca788:	31 c9                	xor    %ecx,%ecx
  3ca78a:	41 86 8f c0 0b 00 00 	xchg   %cl,0xbc0(%r15)
  3ca791:	a8 01                	test   $0x1,%al
  3ca793:	0f 84 02 05 00 00    	je     3cac9b <_ZN5MCLoc20DoNormalUpdateActionEv+0x85b>
  3ca799:	48 8d bc 24 18 01 00 	lea    0x118(%rsp),%rdi
  3ca7a0:	00 
  3ca7a1:	be 18 00 00 00       	mov    $0x18,%esi
  3ca7a6:	e8 65 a6 de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3ca7ab:	48 8d 5c 24 68       	lea    0x68(%rsp),%rbx
  3ca7b0:	48 89 5c 24 58       	mov    %rbx,0x58(%rsp)
  3ca7b5:	49 8d 8f e0 19 00 00 	lea    0x19e0(%r15),%rcx
  3ca7bc:	48 b8 64 61 74 65 4d 	movabs $0x65646f4d65746164,%rax
  3ca7c3:	6f 64 65 
  3ca7c6:	48 89 44 24 6f       	mov    %rax,0x6f(%rsp)
  3ca7cb:	48 b8 4d 43 4c 6f 63 	movabs $0x647055636f4c434d,%rax
  3ca7d2:	55 70 64 
  3ca7d5:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3ca7da:	48 c7 44 24 60 0f 00 	movq   $0xf,0x60(%rsp)
  3ca7e1:	00 00 
  3ca7e3:	c6 44 24 77 00       	movb   $0x0,0x77(%rsp)
  3ca7e8:	4d 8d 87 e8 19 00 00 	lea    0x19e8(%r15),%r8
  3ca7ef:	48 8d 7c 24 78       	lea    0x78(%rsp),%rdi
  3ca7f4:	48 8d 74 24 58       	lea    0x58(%rsp),%rsi
  3ca7f9:	48 8d 94 24 e8 00 00 	lea    0xe8(%rsp),%rdx
  3ca800:	00 
  3ca801:	e8 2a c5 de ff       	call   1b6d30 <_Z9formatLogIJdddEENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEERKS5_DpRKT_@plt>
  3ca806:	4c 89 bc 24 c0 00 00 	mov    %r15,0xc0(%rsp)
  3ca80d:	00 
  3ca80e:	48 8d bc 24 28 01 00 	lea    0x128(%rsp),%rdi
  3ca815:	00 
  3ca816:	48 8b 74 24 78       	mov    0x78(%rsp),%rsi
  3ca81b:	48 8b 94 24 80 00 00 	mov    0x80(%rsp),%rdx
  3ca822:	00 
  3ca823:	e8 c8 62 de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3ca828:	48 8b 7c 24 78       	mov    0x78(%rsp),%rdi
  3ca82d:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3ca834:	00 
  3ca835:	4c 39 ff             	cmp    %r15,%rdi
  3ca838:	74 05                	je     3ca83f <_ZN5MCLoc20DoNormalUpdateActionEv+0x3ff>
  3ca83a:	e8 b1 50 de ff       	call   1af8f0 <_ZdlPv@plt>
  3ca83f:	48 8b 7c 24 58       	mov    0x58(%rsp),%rdi
  3ca844:	48 39 df             	cmp    %rbx,%rdi
  3ca847:	74 05                	je     3ca84e <_ZN5MCLoc20DoNormalUpdateActionEv+0x40e>
  3ca849:	e8 a2 50 de ff       	call   1af8f0 <_ZdlPv@plt>
  3ca84e:	48 8d b4 24 30 01 00 	lea    0x130(%rsp),%rsi
  3ca855:	00 
  3ca856:	48 8d bc 24 c8 00 00 	lea    0xc8(%rsp),%rdi
  3ca85d:	00 
  3ca85e:	e8 fd a3 de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3ca863:	e8 78 d0 de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3ca868:	49 89 c4             	mov    %rax,%r12
  3ca86b:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3ca870:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3ca875:	4c 8b ac 24 c8 00 00 	mov    0xc8(%rsp),%r13
  3ca87c:	00 
  3ca87d:	48 8b 9c 24 d0 00 00 	mov    0xd0(%rsp),%rbx
  3ca884:	00 
  3ca885:	4d 85 ed             	test   %r13,%r13
  3ca888:	75 09                	jne    3ca893 <_ZN5MCLoc20DoNormalUpdateActionEv+0x453>
  3ca88a:	48 85 db             	test   %rbx,%rbx
  3ca88d:	0f 85 4f 33 00 00    	jne    3cdbe2 <_ZN5MCLoc20DoNormalUpdateActionEv+0x37a2>
  3ca893:	49 89 ce             	mov    %rcx,%r14
  3ca896:	48 83 fb 10          	cmp    $0x10,%rbx
  3ca89a:	72 24                	jb     3ca8c0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x480>
  3ca89c:	48 85 db             	test   %rbx,%rbx
  3ca89f:	0f 88 61 33 00 00    	js     3cdc06 <_ZN5MCLoc20DoNormalUpdateActionEv+0x37c6>
  3ca8a5:	48 8d 7b 01          	lea    0x1(%rbx),%rdi
  3ca8a9:	e8 b2 c9 de ff       	call   1b7260 <_Znwm@plt>
  3ca8ae:	49 89 c6             	mov    %rax,%r14
  3ca8b1:	4c 89 74 24 28       	mov    %r14,0x28(%rsp)
  3ca8b6:	48 89 5c 24 38       	mov    %rbx,0x38(%rsp)
  3ca8bb:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3ca8c0:	48 85 db             	test   %rbx,%rbx
  3ca8c3:	74 2b                	je     3ca8f0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4b0>
  3ca8c5:	48 83 fb 01          	cmp    $0x1,%rbx
  3ca8c9:	75 09                	jne    3ca8d4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x494>
  3ca8cb:	41 8a 45 00          	mov    0x0(%r13),%al
  3ca8cf:	41 88 06             	mov    %al,(%r14)
  3ca8d2:	eb 1c                	jmp    3ca8f0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4b0>
  3ca8d4:	49 89 cf             	mov    %rcx,%r15
  3ca8d7:	4c 89 f7             	mov    %r14,%rdi
  3ca8da:	4c 89 ee             	mov    %r13,%rsi
  3ca8dd:	48 89 da             	mov    %rbx,%rdx
  3ca8e0:	e8 9b c6 de ff       	call   1b6f80 <memcpy@plt>
  3ca8e5:	4c 89 f9             	mov    %r15,%rcx
  3ca8e8:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3ca8ef:	00 
  3ca8f0:	48 89 5c 24 30       	mov    %rbx,0x30(%rsp)
  3ca8f5:	41 c6 04 1e 00       	movb   $0x0,(%r14,%rbx,1)
  3ca8fa:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3ca8ff:	48 8b 5c 24 28       	mov    0x28(%rsp),%rbx
  3ca904:	48 39 cb             	cmp    %rcx,%rbx
  3ca907:	74 14                	je     3ca91d <_ZN5MCLoc20DoNormalUpdateActionEv+0x4dd>
  3ca909:	48 89 5c 24 78       	mov    %rbx,0x78(%rsp)
  3ca90e:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3ca913:	48 89 84 24 88 00 00 	mov    %rax,0x88(%rsp)
  3ca91a:	00 
  3ca91b:	eb 0c                	jmp    3ca929 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4e9>
  3ca91d:	f3 0f 6f 01          	movdqu (%rcx),%xmm0
  3ca921:	f3 41 0f 7f 07       	movdqu %xmm0,(%r15)
  3ca926:	4c 89 fb             	mov    %r15,%rbx
  3ca929:	4c 8b 74 24 30       	mov    0x30(%rsp),%r14
  3ca92e:	4c 89 b4 24 80 00 00 	mov    %r14,0x80(%rsp)
  3ca935:	00 
  3ca936:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3ca93b:	48 c7 44 24 30 00 00 	movq   $0x0,0x30(%rsp)
  3ca942:	00 00 
  3ca944:	c6 44 24 38 00       	movb   $0x0,0x38(%rsp)
  3ca949:	48 c7 44 24 68 00 00 	movq   $0x0,0x68(%rsp)
  3ca950:	00 00 
  3ca952:	bf 28 00 00 00       	mov    $0x28,%edi
  3ca957:	e8 04 c9 de ff       	call   1b7260 <_Znwm@plt>
  3ca95c:	48 89 c1             	mov    %rax,%rcx
  3ca95f:	48 83 c1 10          	add    $0x10,%rcx
  3ca963:	48 89 08             	mov    %rcx,(%rax)
  3ca966:	4c 39 fb             	cmp    %r15,%rbx
  3ca969:	74 11                	je     3ca97c <_ZN5MCLoc20DoNormalUpdateActionEv+0x53c>
  3ca96b:	48 89 18             	mov    %rbx,(%rax)
  3ca96e:	48 8b 8c 24 88 00 00 	mov    0x88(%rsp),%rcx
  3ca975:	00 
  3ca976:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3ca97a:	eb 09                	jmp    3ca985 <_ZN5MCLoc20DoNormalUpdateActionEv+0x545>
  3ca97c:	f3 41 0f 6f 07       	movdqu (%r15),%xmm0
  3ca981:	f3 0f 7f 01          	movdqu %xmm0,(%rcx)
  3ca985:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3ca98a:	48 c7 84 24 80 00 00 	movq   $0x0,0x80(%rsp)
  3ca991:	00 00 00 00 00 
  3ca996:	c6 84 24 88 00 00 00 	movb   $0x0,0x88(%rsp)
  3ca99d:	00 
  3ca99e:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3ca9a2:	48 89 44 24 58       	mov    %rax,0x58(%rsp)
  3ca9a7:	48 8d 05 22 9b 01 00 	lea    0x19b22(%rip),%rax        # 3e44d0 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_24vEEE9_M_invokeERKSt9_Any_data>
  3ca9ae:	48 89 44 24 70       	mov    %rax,0x70(%rsp)
  3ca9b3:	48 8d 05 f6 9c 01 00 	lea    0x19cf6(%rip),%rax        # 3e46b0 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_24vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3ca9ba:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3ca9bf:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3ca9c6:	00 00 
  3ca9c8:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3ca9cd:	48 8d 94 24 a0 00 00 	lea    0xa0(%rsp),%rdx
  3ca9d4:	00 
  3ca9d5:	48 8d 4c 24 58       	lea    0x58(%rsp),%rcx
  3ca9da:	31 f6                	xor    %esi,%esi
  3ca9dc:	e8 af 92 de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3ca9e1:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3ca9e6:	48 85 ff             	test   %rdi,%rdi
  3ca9e9:	4c 8b bc 24 c0 00 00 	mov    0xc0(%rsp),%r15
  3ca9f0:	00 
  3ca9f1:	74 17                	je     3caa0a <_ZN5MCLoc20DoNormalUpdateActionEv+0x5ca>
  3ca9f3:	48 8b 07             	mov    (%rdi),%rax
  3ca9f6:	48 8b 35 d3 ef 52 00 	mov    0x52efd3(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3ca9fd:	ff 50 20             	call   *0x20(%rax)
  3caa00:	48 89 c3             	mov    %rax,%rbx
  3caa03:	4c 8b 6c 24 50       	mov    0x50(%rsp),%r13
  3caa08:	eb 05                	jmp    3caa0f <_ZN5MCLoc20DoNormalUpdateActionEv+0x5cf>
  3caa0a:	45 31 ed             	xor    %r13d,%r13d
  3caa0d:	31 db                	xor    %ebx,%ebx
  3caa0f:	48 89 5c 24 48       	mov    %rbx,0x48(%rsp)
  3caa14:	4d 85 ed             	test   %r13,%r13
  3caa17:	74 17                	je     3caa30 <_ZN5MCLoc20DoNormalUpdateActionEv+0x5f0>
  3caa19:	48 83 3d 0f f1 52 00 	cmpq   $0x0,0x52f10f(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3caa20:	00 
  3caa21:	74 08                	je     3caa2b <_ZN5MCLoc20DoNormalUpdateActionEv+0x5eb>
  3caa23:	f0 41 83 45 08 01    	lock addl $0x1,0x8(%r13)
  3caa29:	eb 05                	jmp    3caa30 <_ZN5MCLoc20DoNormalUpdateActionEv+0x5f0>
  3caa2b:	41 83 45 08 01       	addl   $0x1,0x8(%r13)
  3caa30:	48 c7 84 24 b0 00 00 	movq   $0x0,0xb0(%rsp)
  3caa37:	00 00 00 00 00 
  3caa3c:	bf 10 00 00 00       	mov    $0x10,%edi
  3caa41:	e8 1a c8 de ff       	call   1b7260 <_Znwm@plt>
  3caa46:	48 89 18             	mov    %rbx,(%rax)
  3caa49:	4c 89 68 08          	mov    %r13,0x8(%rax)
  3caa4d:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3caa54:	00 
  3caa55:	48 8d 05 84 9d 01 00 	lea    0x19d84(%rip),%rax        # 3e47e0 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_24JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3caa5c:	48 89 84 24 b8 00 00 	mov    %rax,0xb8(%rsp)
  3caa63:	00 
  3caa64:	48 8d 05 a5 9d 01 00 	lea    0x19da5(%rip),%rax        # 3e4810 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_24JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3caa6b:	48 89 84 24 b0 00 00 	mov    %rax,0xb0(%rsp)
  3caa72:	00 
  3caa73:	49 8d 7c 24 08       	lea    0x8(%r12),%rdi
  3caa78:	48 8d b4 24 a0 00 00 	lea    0xa0(%rsp),%rsi
  3caa7f:	00 
  3caa80:	e8 7b 73 de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3caa85:	49 81 c4 c0 01 00 00 	add    $0x1c0,%r12
  3caa8c:	4c 89 e7             	mov    %r12,%rdi
  3caa8f:	e8 dc d6 de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3caa94:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3caa99:	48 8d bc 24 f0 03 00 	lea    0x3f0(%rsp),%rdi
  3caaa0:	00 
  3caaa1:	e8 2a e6 de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3caaa6:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3caaad:	00 
  3caaae:	48 85 c0             	test   %rax,%rax
  3caab1:	74 12                	je     3caac5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x685>
  3caab3:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3caaba:	00 
  3caabb:	ba 03 00 00 00       	mov    $0x3,%edx
  3caac0:	48 89 fe             	mov    %rdi,%rsi
  3caac3:	ff d0                	call   *%rax
  3caac5:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3caaca:	48 85 db             	test   %rbx,%rbx
  3caacd:	74 64                	je     3cab33 <_ZN5MCLoc20DoNormalUpdateActionEv+0x6f3>
  3caacf:	48 83 3d 59 f0 52 00 	cmpq   $0x0,0x52f059(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3caad6:	00 
  3caad7:	74 11                	je     3caaea <_ZN5MCLoc20DoNormalUpdateActionEv+0x6aa>
  3caad9:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3caade:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3caae3:	83 f8 01             	cmp    $0x1,%eax
  3caae6:	74 10                	je     3caaf8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x6b8>
  3caae8:	eb 49                	jmp    3cab33 <_ZN5MCLoc20DoNormalUpdateActionEv+0x6f3>
  3caaea:	8b 43 08             	mov    0x8(%rbx),%eax
  3caaed:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3caaf0:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3caaf3:	83 f8 01             	cmp    $0x1,%eax
  3caaf6:	75 3b                	jne    3cab33 <_ZN5MCLoc20DoNormalUpdateActionEv+0x6f3>
  3caaf8:	48 8b 03             	mov    (%rbx),%rax
  3caafb:	48 89 df             	mov    %rbx,%rdi
  3caafe:	ff 50 10             	call   *0x10(%rax)
  3cab01:	48 83 3d 27 f0 52 00 	cmpq   $0x0,0x52f027(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cab08:	00 
  3cab09:	74 11                	je     3cab1c <_ZN5MCLoc20DoNormalUpdateActionEv+0x6dc>
  3cab0b:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cab10:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cab15:	83 f8 01             	cmp    $0x1,%eax
  3cab18:	74 10                	je     3cab2a <_ZN5MCLoc20DoNormalUpdateActionEv+0x6ea>
  3cab1a:	eb 17                	jmp    3cab33 <_ZN5MCLoc20DoNormalUpdateActionEv+0x6f3>
  3cab1c:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cab1f:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cab22:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cab25:	83 f8 01             	cmp    $0x1,%eax
  3cab28:	75 09                	jne    3cab33 <_ZN5MCLoc20DoNormalUpdateActionEv+0x6f3>
  3cab2a:	48 8b 03             	mov    (%rbx),%rax
  3cab2d:	48 89 df             	mov    %rbx,%rdi
  3cab30:	ff 50 18             	call   *0x18(%rax)
  3cab33:	48 8b 44 24 68       	mov    0x68(%rsp),%rax
  3cab38:	48 85 c0             	test   %rax,%rax
  3cab3b:	74 0f                	je     3cab4c <_ZN5MCLoc20DoNormalUpdateActionEv+0x70c>
  3cab3d:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3cab42:	ba 03 00 00 00       	mov    $0x3,%edx
  3cab47:	48 89 fe             	mov    %rdi,%rsi
  3cab4a:	ff d0                	call   *%rax
  3cab4c:	48 8b 9c 24 f8 03 00 	mov    0x3f8(%rsp),%rbx
  3cab53:	00 
  3cab54:	48 85 db             	test   %rbx,%rbx
  3cab57:	74 64                	je     3cabbd <_ZN5MCLoc20DoNormalUpdateActionEv+0x77d>
  3cab59:	48 83 3d cf ef 52 00 	cmpq   $0x0,0x52efcf(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cab60:	00 
  3cab61:	74 11                	je     3cab74 <_ZN5MCLoc20DoNormalUpdateActionEv+0x734>
  3cab63:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cab68:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cab6d:	83 f8 01             	cmp    $0x1,%eax
  3cab70:	74 10                	je     3cab82 <_ZN5MCLoc20DoNormalUpdateActionEv+0x742>
  3cab72:	eb 49                	jmp    3cabbd <_ZN5MCLoc20DoNormalUpdateActionEv+0x77d>
  3cab74:	8b 43 08             	mov    0x8(%rbx),%eax
  3cab77:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cab7a:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cab7d:	83 f8 01             	cmp    $0x1,%eax
  3cab80:	75 3b                	jne    3cabbd <_ZN5MCLoc20DoNormalUpdateActionEv+0x77d>
  3cab82:	48 8b 03             	mov    (%rbx),%rax
  3cab85:	48 89 df             	mov    %rbx,%rdi
  3cab88:	ff 50 10             	call   *0x10(%rax)
  3cab8b:	48 83 3d 9d ef 52 00 	cmpq   $0x0,0x52ef9d(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cab92:	00 
  3cab93:	74 11                	je     3caba6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x766>
  3cab95:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cab9a:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cab9f:	83 f8 01             	cmp    $0x1,%eax
  3caba2:	74 10                	je     3cabb4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x774>
  3caba4:	eb 17                	jmp    3cabbd <_ZN5MCLoc20DoNormalUpdateActionEv+0x77d>
  3caba6:	8b 43 0c             	mov    0xc(%rbx),%eax
  3caba9:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cabac:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cabaf:	83 f8 01             	cmp    $0x1,%eax
  3cabb2:	75 09                	jne    3cabbd <_ZN5MCLoc20DoNormalUpdateActionEv+0x77d>
  3cabb4:	48 8b 03             	mov    (%rbx),%rax
  3cabb7:	48 89 df             	mov    %rbx,%rdi
  3cabba:	ff 50 18             	call   *0x18(%rax)
  3cabbd:	48 8b 7c 24 28       	mov    0x28(%rsp),%rdi
  3cabc2:	48 8d 44 24 38       	lea    0x38(%rsp),%rax
  3cabc7:	48 39 c7             	cmp    %rax,%rdi
  3cabca:	74 05                	je     3cabd1 <_ZN5MCLoc20DoNormalUpdateActionEv+0x791>
  3cabcc:	e8 1f 4d de ff       	call   1af8f0 <_ZdlPv@plt>
  3cabd1:	48 8b bc 24 c8 00 00 	mov    0xc8(%rsp),%rdi
  3cabd8:	00 
  3cabd9:	48 8d 84 24 d8 00 00 	lea    0xd8(%rsp),%rax
  3cabe0:	00 
  3cabe1:	48 39 c7             	cmp    %rax,%rdi
  3cabe4:	74 05                	je     3cabeb <_ZN5MCLoc20DoNormalUpdateActionEv+0x7ab>
  3cabe6:	e8 05 4d de ff       	call   1af8f0 <_ZdlPv@plt>
  3cabeb:	48 8b 1d d6 fe 52 00 	mov    0x52fed6(%rip),%rbx        # 8faac8 <_ZTTNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cabf2:	48 8b 03             	mov    (%rbx),%rax
  3cabf5:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cabfc:	00 
  3cabfd:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  3cac01:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cac05:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cac0c:	00 
  3cac0d:	48 8b 43 48          	mov    0x48(%rbx),%rax
  3cac11:	48 89 84 24 28 01 00 	mov    %rax,0x128(%rsp)
  3cac18:	00 
  3cac19:	48 8b 05 d0 c6 52 00 	mov    0x52c6d0(%rip),%rax        # 8f72f0 <_ZTVNSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cac20:	48 83 c0 10          	add    $0x10,%rax
  3cac24:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cac2b:	00 
  3cac2c:	48 8b bc 24 78 01 00 	mov    0x178(%rsp),%rdi
  3cac33:	00 
  3cac34:	48 8d 84 24 88 01 00 	lea    0x188(%rsp),%rax
  3cac3b:	00 
  3cac3c:	48 39 c7             	cmp    %rax,%rdi
  3cac3f:	74 05                	je     3cac46 <_ZN5MCLoc20DoNormalUpdateActionEv+0x806>
  3cac41:	e8 aa 4c de ff       	call   1af8f0 <_ZdlPv@plt>
  3cac46:	48 8b 05 03 de 52 00 	mov    0x52de03(%rip),%rax        # 8f8a50 <_ZTVSt15basic_streambufIcSt11char_traitsIcEE@GLIBCXX_3.4>
  3cac4d:	48 83 c0 10          	add    $0x10,%rax
  3cac51:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cac58:	00 
  3cac59:	48 8d bc 24 68 01 00 	lea    0x168(%rsp),%rdi
  3cac60:	00 
  3cac61:	e8 9a 8e de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3cac66:	48 8b 43 10          	mov    0x10(%rbx),%rax
  3cac6a:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  3cac6e:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cac75:	00 
  3cac76:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cac7a:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cac81:	00 
  3cac82:	48 c7 84 24 20 01 00 	movq   $0x0,0x120(%rsp)
  3cac89:	00 00 00 00 00 
  3cac8e:	48 8d bc 24 98 01 00 	lea    0x198(%rsp),%rdi
  3cac95:	00 
  3cac96:	e8 25 da de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3cac9b:	49 8b bf a8 d2 d0 03 	mov    0x3d0d2a8(%r15),%rdi
  3caca2:	f3 41 0f 7e 87 e0 19 	movq   0x19e0(%r15),%xmm0
  3caca9:	00 00 
  3cacab:	f3 41 0f 7e 8f e8 19 	movq   0x19e8(%r15),%xmm1
  3cacb2:	00 00 
  3cacb4:	48 8b 84 24 d8 02 00 	mov    0x2d8(%rsp),%rax
  3cacbb:	00 
  3cacbc:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
  3cacc1:	66 0f 10 94 24 c8 02 	movupd 0x2c8(%rsp),%xmm2
  3cacc8:	00 00 
  3cacca:	66 0f 11 14 24       	movupd %xmm2,(%rsp)
  3caccf:	e8 cc b5 de ff       	call   1b62a0 <_ZN3rbk9algorithm16MCLMotionModel2D18setExtraMoveParamsEddNS0_10StateVar2DE@plt>
  3cacd4:	48 8d 94 24 a0 02 00 	lea    0x2a0(%rsp),%rdx
  3cacdb:	00 
  3cacdc:	be 03 00 00 00       	mov    $0x3,%esi
  3cace1:	48 8b bc 24 f8 00 00 	mov    0xf8(%rsp),%rdi
  3cace8:	00 
  3cace9:	e8 02 41 de ff       	call   1aedf0 <_ZN3rbk9algorithm16ParticleFilter2D15ParticlesActionENS1_9Whats2RunERSt6vectorIdSaIdEE@plt>
  3cacee:	f2 0f 10 84 24 f0 00 	movsd  0xf0(%rsp),%xmm0
  3cacf5:	00 00 
  3cacf7:	66 41 0f 2e 87 88 d2 	ucomisd 0x3d0d288(%r15),%xmm0
  3cacfe:	d0 03 
  3cad00:	66 0f 6f 8c 24 00 01 	movdqa 0x100(%rsp),%xmm1
  3cad07:	00 00 
  3cad09:	66 0f db 0d df 7d 19 	pand   0x197ddf(%rip),%xmm1        # 562af0 <_ZTS11errorLogger+0x1a6>
  3cad10:	00 
  3cad11:	f3 41 0f 7e 87 90 d2 	movq   0x3d0d290(%r15),%xmm0
  3cad18:	d0 03 
  3cad1a:	0f 86 c8 01 00 00    	jbe    3caee8 <_ZN5MCLoc20DoNormalUpdateActionEv+0xaa8>
  3cad20:	66 0f 2e c8          	ucomisd %xmm0,%xmm1
  3cad24:	f3 0f 7e 84 24 b8 02 	movq   0x2b8(%rsp),%xmm0
  3cad2b:	00 00 
  3cad2d:	f3 41 0f 7e 8f 50 d2 	movq   0x3d0d250(%r15),%xmm1
  3cad34:	d0 03 
  3cad36:	0f 86 63 03 00 00    	jbe    3cb09f <_ZN5MCLoc20DoNormalUpdateActionEv+0xc5f>
  3cad3c:	66 0f 2e c8          	ucomisd %xmm0,%xmm1
  3cad40:	0f 86 f8 04 00 00    	jbe    3cb23e <_ZN5MCLoc20DoNormalUpdateActionEv+0xdfe>
  3cad46:	48 b8 00 00 00 00 00 	movabs $0x3ff0000000000000,%rax
  3cad4d:	00 f0 3f 
  3cad50:	48 89 84 24 e8 00 00 	mov    %rax,0xe8(%rsp)
  3cad57:	00 
  3cad58:	41 8a 87 28 0c 00 00 	mov    0xc28(%r15),%al
  3cad5f:	31 c9                	xor    %ecx,%ecx
  3cad61:	41 86 8f c0 0b 00 00 	xchg   %cl,0xbc0(%r15)
  3cad68:	a8 01                	test   $0x1,%al
  3cad6a:	0f 84 bd 29 00 00    	je     3cd72d <_ZN5MCLoc20DoNormalUpdateActionEv+0x32ed>
  3cad70:	48 8d bc 24 18 01 00 	lea    0x118(%rsp),%rdi
  3cad77:	00 
  3cad78:	be 18 00 00 00       	mov    $0x18,%esi
  3cad7d:	e8 8e a0 de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3cad82:	48 8d 5c 24 68       	lea    0x68(%rsp),%rbx
  3cad87:	48 89 5c 24 58       	mov    %rbx,0x58(%rsp)
  3cad8c:	48 b8 64 61 74 65 4d 	movabs $0x65646f4d65746164,%rax
  3cad93:	6f 64 65 
  3cad96:	48 89 44 24 6f       	mov    %rax,0x6f(%rsp)
  3cad9b:	48 b8 4d 43 4c 6f 63 	movabs $0x647055636f4c434d,%rax
  3cada2:	55 70 64 
  3cada5:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cadaa:	48 c7 44 24 60 0f 00 	movq   $0xf,0x60(%rsp)
  3cadb1:	00 00 
  3cadb3:	c6 44 24 77 00       	movb   $0x0,0x77(%rsp)
  3cadb8:	49 8b 87 e8 c5 d0 03 	mov    0x3d0c5e8(%r15),%rax
  3cadbf:	31 c9                	xor    %ecx,%ecx
  3cadc1:	41 86 8f 80 c5 d0 03 	xchg   %cl,0x3d0c580(%r15)
  3cadc8:	31 c9                	xor    %ecx,%ecx
  3cadca:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3cadd1:	00 
  3cadd2:	49 8b 87 b8 c6 d0 03 	mov    0x3d0c6b8(%r15),%rax
  3cadd9:	41 86 8f 50 c6 d0 03 	xchg   %cl,0x3d0c650(%r15)
  3cade0:	48 89 84 24 c8 00 00 	mov    %rax,0xc8(%rsp)
  3cade7:	00 
  3cade8:	48 8d 7c 24 78       	lea    0x78(%rsp),%rdi
  3caded:	48 8d 74 24 58       	lea    0x58(%rsp),%rsi
  3cadf2:	48 8d 94 24 e8 00 00 	lea    0xe8(%rsp),%rdx
  3cadf9:	00 
  3cadfa:	48 8d 8c 24 a0 00 00 	lea    0xa0(%rsp),%rcx
  3cae01:	00 
  3cae02:	4c 8d 84 24 c8 00 00 	lea    0xc8(%rsp),%r8
  3cae09:	00 
  3cae0a:	e8 21 bf de ff       	call   1b6d30 <_Z9formatLogIJdddEENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEERKS5_DpRKT_@plt>
  3cae0f:	4c 89 bc 24 c0 00 00 	mov    %r15,0xc0(%rsp)
  3cae16:	00 
  3cae17:	48 8d bc 24 28 01 00 	lea    0x128(%rsp),%rdi
  3cae1e:	00 
  3cae1f:	48 8b 74 24 78       	mov    0x78(%rsp),%rsi
  3cae24:	48 8b 94 24 80 00 00 	mov    0x80(%rsp),%rdx
  3cae2b:	00 
  3cae2c:	e8 bf 5c de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3cae31:	48 8b 7c 24 78       	mov    0x78(%rsp),%rdi
  3cae36:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3cae3d:	00 
  3cae3e:	4c 39 ff             	cmp    %r15,%rdi
  3cae41:	74 05                	je     3cae48 <_ZN5MCLoc20DoNormalUpdateActionEv+0xa08>
  3cae43:	e8 a8 4a de ff       	call   1af8f0 <_ZdlPv@plt>
  3cae48:	48 8b 7c 24 58       	mov    0x58(%rsp),%rdi
  3cae4d:	48 39 df             	cmp    %rbx,%rdi
  3cae50:	74 05                	je     3cae57 <_ZN5MCLoc20DoNormalUpdateActionEv+0xa17>
  3cae52:	e8 99 4a de ff       	call   1af8f0 <_ZdlPv@plt>
  3cae57:	48 8d b4 24 30 01 00 	lea    0x130(%rsp),%rsi
  3cae5e:	00 
  3cae5f:	48 8d bc 24 c8 00 00 	lea    0xc8(%rsp),%rdi
  3cae66:	00 
  3cae67:	e8 f4 9d de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3cae6c:	e8 6f ca de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3cae71:	49 89 c4             	mov    %rax,%r12
  3cae74:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cae79:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cae7e:	4c 8b ac 24 c8 00 00 	mov    0xc8(%rsp),%r13
  3cae85:	00 
  3cae86:	48 8b 9c 24 d0 00 00 	mov    0xd0(%rsp),%rbx
  3cae8d:	00 
  3cae8e:	4d 85 ed             	test   %r13,%r13
  3cae91:	75 09                	jne    3cae9c <_ZN5MCLoc20DoNormalUpdateActionEv+0xa5c>
  3cae93:	48 85 db             	test   %rbx,%rbx
  3cae96:	0f 85 9a 2d 00 00    	jne    3cdc36 <_ZN5MCLoc20DoNormalUpdateActionEv+0x37f6>
  3cae9c:	49 89 ce             	mov    %rcx,%r14
  3cae9f:	48 83 fb 10          	cmp    $0x10,%rbx
  3caea3:	72 24                	jb     3caec9 <_ZN5MCLoc20DoNormalUpdateActionEv+0xa89>
  3caea5:	48 85 db             	test   %rbx,%rbx
  3caea8:	0f 88 d0 2d 00 00    	js     3cdc7e <_ZN5MCLoc20DoNormalUpdateActionEv+0x383e>
  3caeae:	48 8d 7b 01          	lea    0x1(%rbx),%rdi
  3caeb2:	e8 a9 c3 de ff       	call   1b7260 <_Znwm@plt>
  3caeb7:	49 89 c6             	mov    %rax,%r14
  3caeba:	4c 89 74 24 28       	mov    %r14,0x28(%rsp)
  3caebf:	48 89 5c 24 38       	mov    %rbx,0x38(%rsp)
  3caec4:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3caec9:	48 85 db             	test   %rbx,%rbx
  3caecc:	0f 84 f7 1e 00 00    	je     3ccdc9 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2989>
  3caed2:	48 83 fb 01          	cmp    $0x1,%rbx
  3caed6:	0f 85 d1 1e 00 00    	jne    3ccdad <_ZN5MCLoc20DoNormalUpdateActionEv+0x296d>
  3caedc:	41 8a 45 00          	mov    0x0(%r13),%al
  3caee0:	41 88 06             	mov    %al,(%r14)
  3caee3:	e9 e1 1e 00 00       	jmp    3ccdc9 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2989>
  3caee8:	66 0f 2e c8          	ucomisd %xmm0,%xmm1
  3caeec:	0f 86 f0 04 00 00    	jbe    3cb3e2 <_ZN5MCLoc20DoNormalUpdateActionEv+0xfa2>
  3caef2:	f3 41 0f 7e 87 50 d2 	movq   0x3d0d250(%r15),%xmm0
  3caef9:	d0 03 
  3caefb:	66 0f 2e 84 24 b8 02 	ucomisd 0x2b8(%rsp),%xmm0
  3caf02:	00 00 
  3caf04:	0f 86 34 03 00 00    	jbe    3cb23e <_ZN5MCLoc20DoNormalUpdateActionEv+0xdfe>
  3caf0a:	48 b8 00 00 00 00 00 	movabs $0x4008000000000000,%rax
  3caf11:	00 08 40 
  3caf14:	48 89 84 24 e8 00 00 	mov    %rax,0xe8(%rsp)
  3caf1b:	00 
  3caf1c:	41 8a 87 28 0c 00 00 	mov    0xc28(%r15),%al
  3caf23:	31 c9                	xor    %ecx,%ecx
  3caf25:	41 86 8f c0 0b 00 00 	xchg   %cl,0xbc0(%r15)
  3caf2c:	a8 01                	test   $0x1,%al
  3caf2e:	0f 84 84 29 00 00    	je     3cd8b8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3478>
  3caf34:	48 8d bc 24 18 01 00 	lea    0x118(%rsp),%rdi
  3caf3b:	00 
  3caf3c:	be 18 00 00 00       	mov    $0x18,%esi
  3caf41:	e8 ca 9e de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3caf46:	48 8d 5c 24 68       	lea    0x68(%rsp),%rbx
  3caf4b:	48 89 5c 24 58       	mov    %rbx,0x58(%rsp)
  3caf50:	48 b8 64 61 74 65 4d 	movabs $0x65646f4d65746164,%rax
  3caf57:	6f 64 65 
  3caf5a:	48 89 44 24 6f       	mov    %rax,0x6f(%rsp)
  3caf5f:	48 b8 4d 43 4c 6f 63 	movabs $0x647055636f4c434d,%rax
  3caf66:	55 70 64 
  3caf69:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3caf6e:	48 c7 44 24 60 0f 00 	movq   $0xf,0x60(%rsp)
  3caf75:	00 00 
  3caf77:	c6 44 24 77 00       	movb   $0x0,0x77(%rsp)
  3caf7c:	c7 84 24 c8 00 00 00 	movl   $0x5,0xc8(%rsp)
  3caf83:	05 00 00 00 
  3caf87:	49 8b 87 b8 c6 d0 03 	mov    0x3d0c6b8(%r15),%rax
  3caf8e:	31 c9                	xor    %ecx,%ecx
  3caf90:	41 86 8f 50 c6 d0 03 	xchg   %cl,0x3d0c650(%r15)
  3caf97:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3caf9e:	00 
  3caf9f:	48 8d 7c 24 78       	lea    0x78(%rsp),%rdi
  3cafa4:	48 8d 74 24 58       	lea    0x58(%rsp),%rsi
  3cafa9:	48 8d 94 24 e8 00 00 	lea    0xe8(%rsp),%rdx
  3cafb0:	00 
  3cafb1:	48 8d 8c 24 c8 00 00 	lea    0xc8(%rsp),%rcx
  3cafb8:	00 
  3cafb9:	4c 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%r8
  3cafc0:	00 
  3cafc1:	e8 7a 88 de ff       	call   1b3840 <_Z9formatLogIJdidEENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEERKS5_DpRKT_@plt>
  3cafc6:	4c 89 bc 24 c0 00 00 	mov    %r15,0xc0(%rsp)
  3cafcd:	00 
  3cafce:	48 8d bc 24 28 01 00 	lea    0x128(%rsp),%rdi
  3cafd5:	00 
  3cafd6:	48 8b 74 24 78       	mov    0x78(%rsp),%rsi
  3cafdb:	48 8b 94 24 80 00 00 	mov    0x80(%rsp),%rdx
  3cafe2:	00 
  3cafe3:	e8 08 5b de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3cafe8:	48 8b 7c 24 78       	mov    0x78(%rsp),%rdi
  3cafed:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3caff4:	00 
  3caff5:	4c 39 ff             	cmp    %r15,%rdi
  3caff8:	74 05                	je     3cafff <_ZN5MCLoc20DoNormalUpdateActionEv+0xbbf>
  3caffa:	e8 f1 48 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cafff:	48 8b 7c 24 58       	mov    0x58(%rsp),%rdi
  3cb004:	48 39 df             	cmp    %rbx,%rdi
  3cb007:	74 05                	je     3cb00e <_ZN5MCLoc20DoNormalUpdateActionEv+0xbce>
  3cb009:	e8 e2 48 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cb00e:	48 8d b4 24 30 01 00 	lea    0x130(%rsp),%rsi
  3cb015:	00 
  3cb016:	48 8d bc 24 c8 00 00 	lea    0xc8(%rsp),%rdi
  3cb01d:	00 
  3cb01e:	e8 3d 9c de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3cb023:	e8 b8 c8 de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3cb028:	49 89 c4             	mov    %rax,%r12
  3cb02b:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cb030:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cb035:	4c 8b ac 24 c8 00 00 	mov    0xc8(%rsp),%r13
  3cb03c:	00 
  3cb03d:	48 8b 9c 24 d0 00 00 	mov    0xd0(%rsp),%rbx
  3cb044:	00 
  3cb045:	4d 85 ed             	test   %r13,%r13
  3cb048:	75 09                	jne    3cb053 <_ZN5MCLoc20DoNormalUpdateActionEv+0xc13>
  3cb04a:	48 85 db             	test   %rbx,%rbx
  3cb04d:	0f 85 ef 2b 00 00    	jne    3cdc42 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3802>
  3cb053:	49 89 ce             	mov    %rcx,%r14
  3cb056:	48 83 fb 10          	cmp    $0x10,%rbx
  3cb05a:	72 24                	jb     3cb080 <_ZN5MCLoc20DoNormalUpdateActionEv+0xc40>
  3cb05c:	48 85 db             	test   %rbx,%rbx
  3cb05f:	0f 88 25 2c 00 00    	js     3cdc8a <_ZN5MCLoc20DoNormalUpdateActionEv+0x384a>
  3cb065:	48 8d 7b 01          	lea    0x1(%rbx),%rdi
  3cb069:	e8 f2 c1 de ff       	call   1b7260 <_Znwm@plt>
  3cb06e:	49 89 c6             	mov    %rax,%r14
  3cb071:	4c 89 74 24 28       	mov    %r14,0x28(%rsp)
  3cb076:	48 89 5c 24 38       	mov    %rbx,0x38(%rsp)
  3cb07b:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cb080:	48 85 db             	test   %rbx,%rbx
  3cb083:	0f 84 a2 1e 00 00    	je     3ccf2b <_ZN5MCLoc20DoNormalUpdateActionEv+0x2aeb>
  3cb089:	48 83 fb 01          	cmp    $0x1,%rbx
  3cb08d:	0f 85 7c 1e 00 00    	jne    3ccf0f <_ZN5MCLoc20DoNormalUpdateActionEv+0x2acf>
  3cb093:	41 8a 45 00          	mov    0x0(%r13),%al
  3cb097:	41 88 06             	mov    %al,(%r14)
  3cb09a:	e9 8c 1e 00 00       	jmp    3ccf2b <_ZN5MCLoc20DoNormalUpdateActionEv+0x2aeb>
  3cb09f:	66 0f 2e c8          	ucomisd %xmm0,%xmm1
  3cb0a3:	0f 86 95 01 00 00    	jbe    3cb23e <_ZN5MCLoc20DoNormalUpdateActionEv+0xdfe>
  3cb0a9:	48 b8 00 00 00 00 00 	movabs $0x4000000000000000,%rax
  3cb0b0:	00 00 40 
  3cb0b3:	48 89 84 24 e8 00 00 	mov    %rax,0xe8(%rsp)
  3cb0ba:	00 
  3cb0bb:	41 8a 87 28 0c 00 00 	mov    0xc28(%r15),%al
  3cb0c2:	31 c9                	xor    %ecx,%ecx
  3cb0c4:	41 86 8f c0 0b 00 00 	xchg   %cl,0xbc0(%r15)
  3cb0cb:	a8 01                	test   $0x1,%al
  3cb0cd:	0f 84 70 29 00 00    	je     3cda43 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3603>
  3cb0d3:	48 8d bc 24 18 01 00 	lea    0x118(%rsp),%rdi
  3cb0da:	00 
  3cb0db:	be 18 00 00 00       	mov    $0x18,%esi
  3cb0e0:	e8 2b 9d de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3cb0e5:	48 8d 5c 24 68       	lea    0x68(%rsp),%rbx
  3cb0ea:	48 89 5c 24 58       	mov    %rbx,0x58(%rsp)
  3cb0ef:	48 b8 64 61 74 65 4d 	movabs $0x65646f4d65746164,%rax
  3cb0f6:	6f 64 65 
  3cb0f9:	48 89 44 24 6f       	mov    %rax,0x6f(%rsp)
  3cb0fe:	48 b8 4d 43 4c 6f 63 	movabs $0x647055636f4c434d,%rax
  3cb105:	55 70 64 
  3cb108:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cb10d:	48 c7 44 24 60 0f 00 	movq   $0xf,0x60(%rsp)
  3cb114:	00 00 
  3cb116:	c6 44 24 77 00       	movb   $0x0,0x77(%rsp)
  3cb11b:	49 8b 87 e8 c5 d0 03 	mov    0x3d0c5e8(%r15),%rax
  3cb122:	31 c9                	xor    %ecx,%ecx
  3cb124:	41 86 8f 80 c5 d0 03 	xchg   %cl,0x3d0c580(%r15)
  3cb12b:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3cb132:	00 
  3cb133:	c7 84 24 c8 00 00 00 	movl   $0x2,0xc8(%rsp)
  3cb13a:	02 00 00 00 
  3cb13e:	48 8d 7c 24 78       	lea    0x78(%rsp),%rdi
  3cb143:	48 8d 74 24 58       	lea    0x58(%rsp),%rsi
  3cb148:	48 8d 94 24 e8 00 00 	lea    0xe8(%rsp),%rdx
  3cb14f:	00 
  3cb150:	48 8d 8c 24 a0 00 00 	lea    0xa0(%rsp),%rcx
  3cb157:	00 
  3cb158:	4c 8d 84 24 c8 00 00 	lea    0xc8(%rsp),%r8
  3cb15f:	00 
  3cb160:	e8 6b 39 de ff       	call   1aead0 <_Z9formatLogIJddiEENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEERKS5_DpRKT_@plt>
  3cb165:	4c 89 bc 24 c0 00 00 	mov    %r15,0xc0(%rsp)
  3cb16c:	00 
  3cb16d:	48 8d bc 24 28 01 00 	lea    0x128(%rsp),%rdi
  3cb174:	00 
  3cb175:	48 8b 74 24 78       	mov    0x78(%rsp),%rsi
  3cb17a:	48 8b 94 24 80 00 00 	mov    0x80(%rsp),%rdx
  3cb181:	00 
  3cb182:	e8 69 59 de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3cb187:	48 8b 7c 24 78       	mov    0x78(%rsp),%rdi
  3cb18c:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3cb193:	00 
  3cb194:	4c 39 ff             	cmp    %r15,%rdi
  3cb197:	74 05                	je     3cb19e <_ZN5MCLoc20DoNormalUpdateActionEv+0xd5e>
  3cb199:	e8 52 47 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cb19e:	48 8b 7c 24 58       	mov    0x58(%rsp),%rdi
  3cb1a3:	48 39 df             	cmp    %rbx,%rdi
  3cb1a6:	74 05                	je     3cb1ad <_ZN5MCLoc20DoNormalUpdateActionEv+0xd6d>
  3cb1a8:	e8 43 47 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cb1ad:	48 8d b4 24 30 01 00 	lea    0x130(%rsp),%rsi
  3cb1b4:	00 
  3cb1b5:	48 8d bc 24 c8 00 00 	lea    0xc8(%rsp),%rdi
  3cb1bc:	00 
  3cb1bd:	e8 9e 9a de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3cb1c2:	e8 19 c7 de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3cb1c7:	49 89 c4             	mov    %rax,%r12
  3cb1ca:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cb1cf:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cb1d4:	4c 8b ac 24 c8 00 00 	mov    0xc8(%rsp),%r13
  3cb1db:	00 
  3cb1dc:	48 8b 9c 24 d0 00 00 	mov    0xd0(%rsp),%rbx
  3cb1e3:	00 
  3cb1e4:	4d 85 ed             	test   %r13,%r13
  3cb1e7:	75 09                	jne    3cb1f2 <_ZN5MCLoc20DoNormalUpdateActionEv+0xdb2>
  3cb1e9:	48 85 db             	test   %rbx,%rbx
  3cb1ec:	0f 85 5c 2a 00 00    	jne    3cdc4e <_ZN5MCLoc20DoNormalUpdateActionEv+0x380e>
  3cb1f2:	49 89 ce             	mov    %rcx,%r14
  3cb1f5:	48 83 fb 10          	cmp    $0x10,%rbx
  3cb1f9:	72 24                	jb     3cb21f <_ZN5MCLoc20DoNormalUpdateActionEv+0xddf>
  3cb1fb:	48 85 db             	test   %rbx,%rbx
  3cb1fe:	0f 88 92 2a 00 00    	js     3cdc96 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3856>
  3cb204:	48 8d 7b 01          	lea    0x1(%rbx),%rdi
  3cb208:	e8 53 c0 de ff       	call   1b7260 <_Znwm@plt>
  3cb20d:	49 89 c6             	mov    %rax,%r14
  3cb210:	4c 89 74 24 28       	mov    %r14,0x28(%rsp)
  3cb215:	48 89 5c 24 38       	mov    %rbx,0x38(%rsp)
  3cb21a:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cb21f:	48 85 db             	test   %rbx,%rbx
  3cb222:	0f 84 65 1e 00 00    	je     3cd08d <_ZN5MCLoc20DoNormalUpdateActionEv+0x2c4d>
  3cb228:	48 83 fb 01          	cmp    $0x1,%rbx
  3cb22c:	0f 85 3f 1e 00 00    	jne    3cd071 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2c31>
  3cb232:	41 8a 45 00          	mov    0x0(%r13),%al
  3cb236:	41 88 06             	mov    %al,(%r14)
  3cb239:	e9 4f 1e 00 00       	jmp    3cd08d <_ZN5MCLoc20DoNormalUpdateActionEv+0x2c4d>
  3cb23e:	48 b8 00 00 00 00 00 	movabs $0x4014000000000000,%rax
  3cb245:	00 14 40 
  3cb248:	48 89 84 24 e8 00 00 	mov    %rax,0xe8(%rsp)
  3cb24f:	00 
  3cb250:	41 8a 8f 68 cb d0 03 	mov    0x3d0cb68(%r15),%cl
  3cb257:	b8 00 00 00 00       	mov    $0x0,%eax
  3cb25c:	41 86 87 00 cb d0 03 	xchg   %al,0x3d0cb00(%r15)
  3cb263:	31 d2                	xor    %edx,%edx
  3cb265:	41 8a 87 28 0c 00 00 	mov    0xc28(%r15),%al
  3cb26c:	41 86 97 c0 0b 00 00 	xchg   %dl,0xbc0(%r15)
  3cb273:	f6 c1 01             	test   $0x1,%cl
  3cb276:	0f 85 08 03 00 00    	jne    3cb584 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1144>
  3cb27c:	a8 01                	test   $0x1,%al
  3cb27e:	0f 84 9a 08 00 00    	je     3cbb1e <_ZN5MCLoc20DoNormalUpdateActionEv+0x16de>
  3cb284:	48 8d bc 24 18 01 00 	lea    0x118(%rsp),%rdi
  3cb28b:	00 
  3cb28c:	be 18 00 00 00       	mov    $0x18,%esi
  3cb291:	e8 7a 9b de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3cb296:	48 8d 5c 24 68       	lea    0x68(%rsp),%rbx
  3cb29b:	48 89 5c 24 58       	mov    %rbx,0x58(%rsp)
  3cb2a0:	48 b8 64 61 74 65 4d 	movabs $0x65646f4d65746164,%rax
  3cb2a7:	6f 64 65 
  3cb2aa:	48 89 44 24 6f       	mov    %rax,0x6f(%rsp)
  3cb2af:	48 b8 4d 43 4c 6f 63 	movabs $0x647055636f4c434d,%rax
  3cb2b6:	55 70 64 
  3cb2b9:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cb2be:	48 c7 44 24 60 0f 00 	movq   $0xf,0x60(%rsp)
  3cb2c5:	00 00 
  3cb2c7:	c6 44 24 77 00       	movb   $0x0,0x77(%rsp)
  3cb2cc:	c7 84 24 a0 00 00 00 	movl   $0x0,0xa0(%rsp)
  3cb2d3:	00 00 00 00 
  3cb2d7:	c7 84 24 c8 00 00 00 	movl   $0x0,0xc8(%rsp)
  3cb2de:	00 00 00 00 
  3cb2e2:	48 8d 7c 24 78       	lea    0x78(%rsp),%rdi
  3cb2e7:	48 8d 74 24 58       	lea    0x58(%rsp),%rsi
  3cb2ec:	48 8d 94 24 e8 00 00 	lea    0xe8(%rsp),%rdx
  3cb2f3:	00 
  3cb2f4:	48 8d 8c 24 a0 00 00 	lea    0xa0(%rsp),%rcx
  3cb2fb:	00 
  3cb2fc:	4c 8d 84 24 c8 00 00 	lea    0xc8(%rsp),%r8
  3cb303:	00 
  3cb304:	e8 57 d2 de ff       	call   1b8560 <_Z9formatLogIJdiiEENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEERKS5_DpRKT_@plt>
  3cb309:	4c 89 bc 24 c0 00 00 	mov    %r15,0xc0(%rsp)
  3cb310:	00 
  3cb311:	48 8d bc 24 28 01 00 	lea    0x128(%rsp),%rdi
  3cb318:	00 
  3cb319:	48 8b 74 24 78       	mov    0x78(%rsp),%rsi
  3cb31e:	48 8b 94 24 80 00 00 	mov    0x80(%rsp),%rdx
  3cb325:	00 
  3cb326:	e8 c5 57 de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3cb32b:	48 8b 7c 24 78       	mov    0x78(%rsp),%rdi
  3cb330:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3cb337:	00 
  3cb338:	4c 39 ff             	cmp    %r15,%rdi
  3cb33b:	74 05                	je     3cb342 <_ZN5MCLoc20DoNormalUpdateActionEv+0xf02>
  3cb33d:	e8 ae 45 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cb342:	48 8b 7c 24 58       	mov    0x58(%rsp),%rdi
  3cb347:	48 39 df             	cmp    %rbx,%rdi
  3cb34a:	74 05                	je     3cb351 <_ZN5MCLoc20DoNormalUpdateActionEv+0xf11>
  3cb34c:	e8 9f 45 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cb351:	48 8d b4 24 30 01 00 	lea    0x130(%rsp),%rsi
  3cb358:	00 
  3cb359:	48 8d bc 24 c8 00 00 	lea    0xc8(%rsp),%rdi
  3cb360:	00 
  3cb361:	e8 fa 98 de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3cb366:	e8 75 c5 de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3cb36b:	49 89 c4             	mov    %rax,%r12
  3cb36e:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cb373:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cb378:	4c 8b ac 24 c8 00 00 	mov    0xc8(%rsp),%r13
  3cb37f:	00 
  3cb380:	48 8b 9c 24 d0 00 00 	mov    0xd0(%rsp),%rbx
  3cb387:	00 
  3cb388:	4d 85 ed             	test   %r13,%r13
  3cb38b:	75 09                	jne    3cb396 <_ZN5MCLoc20DoNormalUpdateActionEv+0xf56>
  3cb38d:	48 85 db             	test   %rbx,%rbx
  3cb390:	0f 85 88 28 00 00    	jne    3cdc1e <_ZN5MCLoc20DoNormalUpdateActionEv+0x37de>
  3cb396:	49 89 ce             	mov    %rcx,%r14
  3cb399:	48 83 fb 10          	cmp    $0x10,%rbx
  3cb39d:	72 24                	jb     3cb3c3 <_ZN5MCLoc20DoNormalUpdateActionEv+0xf83>
  3cb39f:	48 85 db             	test   %rbx,%rbx
  3cb3a2:	0f 88 be 28 00 00    	js     3cdc66 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3826>
  3cb3a8:	48 8d 7b 01          	lea    0x1(%rbx),%rdi
  3cb3ac:	e8 af be de ff       	call   1b7260 <_Znwm@plt>
  3cb3b1:	49 89 c6             	mov    %rax,%r14
  3cb3b4:	4c 89 74 24 28       	mov    %r14,0x28(%rsp)
  3cb3b9:	48 89 5c 24 38       	mov    %rbx,0x38(%rsp)
  3cb3be:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cb3c3:	48 85 db             	test   %rbx,%rbx
  3cb3c6:	0f 84 ca 11 00 00    	je     3cc596 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2156>
  3cb3cc:	48 83 fb 01          	cmp    $0x1,%rbx
  3cb3d0:	0f 85 a4 11 00 00    	jne    3cc57a <_ZN5MCLoc20DoNormalUpdateActionEv+0x213a>
  3cb3d6:	41 8a 45 00          	mov    0x0(%r13),%al
  3cb3da:	41 88 06             	mov    %al,(%r14)
  3cb3dd:	e9 b4 11 00 00       	jmp    3cc596 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2156>
  3cb3e2:	48 b8 00 00 00 00 00 	movabs $0x4010000000000000,%rax
  3cb3e9:	00 10 40 
  3cb3ec:	48 89 84 24 e8 00 00 	mov    %rax,0xe8(%rsp)
  3cb3f3:	00 
  3cb3f4:	41 8a 87 28 0c 00 00 	mov    0xc28(%r15),%al
  3cb3fb:	31 c9                	xor    %ecx,%ecx
  3cb3fd:	41 86 8f c0 0b 00 00 	xchg   %cl,0xbc0(%r15)
  3cb404:	a8 01                	test   $0x1,%al
  3cb406:	0f 84 a7 06 00 00    	je     3cbab3 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1673>
  3cb40c:	48 8d bc 24 18 01 00 	lea    0x118(%rsp),%rdi
  3cb413:	00 
  3cb414:	be 18 00 00 00       	mov    $0x18,%esi
  3cb419:	e8 f2 99 de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3cb41e:	48 8d 5c 24 68       	lea    0x68(%rsp),%rbx
  3cb423:	48 89 5c 24 58       	mov    %rbx,0x58(%rsp)
  3cb428:	48 b8 64 61 74 65 4d 	movabs $0x65646f4d65746164,%rax
  3cb42f:	6f 64 65 
  3cb432:	48 89 44 24 6f       	mov    %rax,0x6f(%rsp)
  3cb437:	48 b8 4d 43 4c 6f 63 	movabs $0x647055636f4c434d,%rax
  3cb43e:	55 70 64 
  3cb441:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cb446:	48 c7 44 24 60 0f 00 	movq   $0xf,0x60(%rsp)
  3cb44d:	00 00 
  3cb44f:	c6 44 24 77 00       	movb   $0x0,0x77(%rsp)
  3cb454:	49 8b 87 88 c7 d0 03 	mov    0x3d0c788(%r15),%rax
  3cb45b:	31 c9                	xor    %ecx,%ecx
  3cb45d:	41 86 8f 20 c7 d0 03 	xchg   %cl,0x3d0c720(%r15)
  3cb464:	31 c9                	xor    %ecx,%ecx
  3cb466:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3cb46d:	00 
  3cb46e:	49 8b 87 58 c8 d0 03 	mov    0x3d0c858(%r15),%rax
  3cb475:	41 86 8f f0 c7 d0 03 	xchg   %cl,0x3d0c7f0(%r15)
  3cb47c:	48 89 84 24 c8 00 00 	mov    %rax,0xc8(%rsp)
  3cb483:	00 
  3cb484:	48 8d 7c 24 78       	lea    0x78(%rsp),%rdi
  3cb489:	48 8d 74 24 58       	lea    0x58(%rsp),%rsi
  3cb48e:	48 8d 94 24 e8 00 00 	lea    0xe8(%rsp),%rdx
  3cb495:	00 
  3cb496:	48 8d 8c 24 a0 00 00 	lea    0xa0(%rsp),%rcx
  3cb49d:	00 
  3cb49e:	4c 8d 84 24 c8 00 00 	lea    0xc8(%rsp),%r8
  3cb4a5:	00 
  3cb4a6:	e8 85 b8 de ff       	call   1b6d30 <_Z9formatLogIJdddEENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEERKS5_DpRKT_@plt>
  3cb4ab:	4c 89 bc 24 c0 00 00 	mov    %r15,0xc0(%rsp)
  3cb4b2:	00 
  3cb4b3:	48 8d bc 24 28 01 00 	lea    0x128(%rsp),%rdi
  3cb4ba:	00 
  3cb4bb:	48 8b 74 24 78       	mov    0x78(%rsp),%rsi
  3cb4c0:	48 8b 94 24 80 00 00 	mov    0x80(%rsp),%rdx
  3cb4c7:	00 
  3cb4c8:	e8 23 56 de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3cb4cd:	48 8b 7c 24 78       	mov    0x78(%rsp),%rdi
  3cb4d2:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3cb4d9:	00 
  3cb4da:	4c 39 ff             	cmp    %r15,%rdi
  3cb4dd:	74 05                	je     3cb4e4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x10a4>
  3cb4df:	e8 0c 44 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cb4e4:	48 8b 7c 24 58       	mov    0x58(%rsp),%rdi
  3cb4e9:	48 39 df             	cmp    %rbx,%rdi
  3cb4ec:	74 05                	je     3cb4f3 <_ZN5MCLoc20DoNormalUpdateActionEv+0x10b3>
  3cb4ee:	e8 fd 43 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cb4f3:	48 8d b4 24 30 01 00 	lea    0x130(%rsp),%rsi
  3cb4fa:	00 
  3cb4fb:	48 8d bc 24 c8 00 00 	lea    0xc8(%rsp),%rdi
  3cb502:	00 
  3cb503:	e8 58 97 de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3cb508:	e8 d3 c3 de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3cb50d:	49 89 c4             	mov    %rax,%r12
  3cb510:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cb515:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cb51a:	4c 8b ac 24 c8 00 00 	mov    0xc8(%rsp),%r13
  3cb521:	00 
  3cb522:	48 8b 9c 24 d0 00 00 	mov    0xd0(%rsp),%rbx
  3cb529:	00 
  3cb52a:	4d 85 ed             	test   %r13,%r13
  3cb52d:	75 09                	jne    3cb538 <_ZN5MCLoc20DoNormalUpdateActionEv+0x10f8>
  3cb52f:	48 85 db             	test   %rbx,%rbx
  3cb532:	0f 85 da 26 00 00    	jne    3cdc12 <_ZN5MCLoc20DoNormalUpdateActionEv+0x37d2>
  3cb538:	49 89 ce             	mov    %rcx,%r14
  3cb53b:	48 83 fb 10          	cmp    $0x10,%rbx
  3cb53f:	72 24                	jb     3cb565 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1125>
  3cb541:	48 85 db             	test   %rbx,%rbx
  3cb544:	0f 88 10 27 00 00    	js     3cdc5a <_ZN5MCLoc20DoNormalUpdateActionEv+0x381a>
  3cb54a:	48 8d 7b 01          	lea    0x1(%rbx),%rdi
  3cb54e:	e8 0d bd de ff       	call   1b7260 <_Znwm@plt>
  3cb553:	49 89 c6             	mov    %rax,%r14
  3cb556:	4c 89 74 24 28       	mov    %r14,0x28(%rsp)
  3cb55b:	48 89 5c 24 38       	mov    %rbx,0x38(%rsp)
  3cb560:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cb565:	48 85 db             	test   %rbx,%rbx
  3cb568:	0f 84 b2 01 00 00    	je     3cb720 <_ZN5MCLoc20DoNormalUpdateActionEv+0x12e0>
  3cb56e:	48 83 fb 01          	cmp    $0x1,%rbx
  3cb572:	0f 85 8c 01 00 00    	jne    3cb704 <_ZN5MCLoc20DoNormalUpdateActionEv+0x12c4>
  3cb578:	41 8a 45 00          	mov    0x0(%r13),%al
  3cb57c:	41 88 06             	mov    %al,(%r14)
  3cb57f:	e9 9c 01 00 00       	jmp    3cb720 <_ZN5MCLoc20DoNormalUpdateActionEv+0x12e0>
  3cb584:	a8 01                	test   $0x1,%al
  3cb586:	0f 84 b1 17 00 00    	je     3ccd3d <_ZN5MCLoc20DoNormalUpdateActionEv+0x28fd>
  3cb58c:	48 8d bc 24 18 01 00 	lea    0x118(%rsp),%rdi
  3cb593:	00 
  3cb594:	be 18 00 00 00       	mov    $0x18,%esi
  3cb599:	e8 72 98 de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3cb59e:	48 8d 5c 24 68       	lea    0x68(%rsp),%rbx
  3cb5a3:	48 89 5c 24 58       	mov    %rbx,0x58(%rsp)
  3cb5a8:	48 b8 64 61 74 65 4d 	movabs $0x65646f4d65746164,%rax
  3cb5af:	6f 64 65 
  3cb5b2:	48 89 44 24 6f       	mov    %rax,0x6f(%rsp)
  3cb5b7:	48 b8 4d 43 4c 6f 63 	movabs $0x647055636f4c434d,%rax
  3cb5be:	55 70 64 
  3cb5c1:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cb5c6:	48 c7 44 24 60 0f 00 	movq   $0xf,0x60(%rsp)
  3cb5cd:	00 00 
  3cb5cf:	c6 44 24 77 00       	movb   $0x0,0x77(%rsp)
  3cb5d4:	49 8b 87 20 cc d0 03 	mov    0x3d0cc20(%r15),%rax
  3cb5db:	31 c9                	xor    %ecx,%ecx
  3cb5dd:	41 86 8f b8 cb d0 03 	xchg   %cl,0x3d0cbb8(%r15)
  3cb5e4:	31 c9                	xor    %ecx,%ecx
  3cb5e6:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3cb5ed:	00 
  3cb5ee:	49 8b 87 f0 cc d0 03 	mov    0x3d0ccf0(%r15),%rax
  3cb5f5:	41 86 8f 88 cc d0 03 	xchg   %cl,0x3d0cc88(%r15)
  3cb5fc:	48 89 84 24 c8 00 00 	mov    %rax,0xc8(%rsp)
  3cb603:	00 
  3cb604:	48 8d 7c 24 78       	lea    0x78(%rsp),%rdi
  3cb609:	48 8d 74 24 58       	lea    0x58(%rsp),%rsi
  3cb60e:	48 8d 94 24 e8 00 00 	lea    0xe8(%rsp),%rdx
  3cb615:	00 
  3cb616:	48 8d 8c 24 a0 00 00 	lea    0xa0(%rsp),%rcx
  3cb61d:	00 
  3cb61e:	4c 8d 84 24 c8 00 00 	lea    0xc8(%rsp),%r8
  3cb625:	00 
  3cb626:	e8 05 b7 de ff       	call   1b6d30 <_Z9formatLogIJdddEENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEERKS5_DpRKT_@plt>
  3cb62b:	4c 89 bc 24 c0 00 00 	mov    %r15,0xc0(%rsp)
  3cb632:	00 
  3cb633:	48 8d bc 24 28 01 00 	lea    0x128(%rsp),%rdi
  3cb63a:	00 
  3cb63b:	48 8b 74 24 78       	mov    0x78(%rsp),%rsi
  3cb640:	48 8b 94 24 80 00 00 	mov    0x80(%rsp),%rdx
  3cb647:	00 
  3cb648:	e8 a3 54 de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3cb64d:	48 8b 7c 24 78       	mov    0x78(%rsp),%rdi
  3cb652:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3cb659:	00 
  3cb65a:	4c 39 ff             	cmp    %r15,%rdi
  3cb65d:	74 05                	je     3cb664 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1224>
  3cb65f:	e8 8c 42 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cb664:	48 8b 7c 24 58       	mov    0x58(%rsp),%rdi
  3cb669:	48 39 df             	cmp    %rbx,%rdi
  3cb66c:	74 05                	je     3cb673 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1233>
  3cb66e:	e8 7d 42 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cb673:	48 8d b4 24 30 01 00 	lea    0x130(%rsp),%rsi
  3cb67a:	00 
  3cb67b:	48 8d bc 24 c8 00 00 	lea    0xc8(%rsp),%rdi
  3cb682:	00 
  3cb683:	e8 d8 95 de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3cb688:	e8 53 c2 de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3cb68d:	49 89 c4             	mov    %rax,%r12
  3cb690:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cb695:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cb69a:	4c 8b ac 24 c8 00 00 	mov    0xc8(%rsp),%r13
  3cb6a1:	00 
  3cb6a2:	48 8b 9c 24 d0 00 00 	mov    0xd0(%rsp),%rbx
  3cb6a9:	00 
  3cb6aa:	4d 85 ed             	test   %r13,%r13
  3cb6ad:	75 09                	jne    3cb6b8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1278>
  3cb6af:	48 85 db             	test   %rbx,%rbx
  3cb6b2:	0f 85 72 25 00 00    	jne    3cdc2a <_ZN5MCLoc20DoNormalUpdateActionEv+0x37ea>
  3cb6b8:	49 89 ce             	mov    %rcx,%r14
  3cb6bb:	48 83 fb 10          	cmp    $0x10,%rbx
  3cb6bf:	72 24                	jb     3cb6e5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x12a5>
  3cb6c1:	48 85 db             	test   %rbx,%rbx
  3cb6c4:	0f 88 a8 25 00 00    	js     3cdc72 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3832>
  3cb6ca:	48 8d 7b 01          	lea    0x1(%rbx),%rdi
  3cb6ce:	e8 8d bb de ff       	call   1b7260 <_Znwm@plt>
  3cb6d3:	49 89 c6             	mov    %rax,%r14
  3cb6d6:	4c 89 74 24 28       	mov    %r14,0x28(%rsp)
  3cb6db:	48 89 5c 24 38       	mov    %rbx,0x38(%rsp)
  3cb6e0:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cb6e5:	48 85 db             	test   %rbx,%rbx
  3cb6e8:	0f 84 0a 10 00 00    	je     3cc6f8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x22b8>
  3cb6ee:	48 83 fb 01          	cmp    $0x1,%rbx
  3cb6f2:	0f 85 e4 0f 00 00    	jne    3cc6dc <_ZN5MCLoc20DoNormalUpdateActionEv+0x229c>
  3cb6f8:	41 8a 45 00          	mov    0x0(%r13),%al
  3cb6fc:	41 88 06             	mov    %al,(%r14)
  3cb6ff:	e9 f4 0f 00 00       	jmp    3cc6f8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x22b8>
  3cb704:	49 89 cf             	mov    %rcx,%r15
  3cb707:	4c 89 f7             	mov    %r14,%rdi
  3cb70a:	4c 89 ee             	mov    %r13,%rsi
  3cb70d:	48 89 da             	mov    %rbx,%rdx
  3cb710:	e8 6b b8 de ff       	call   1b6f80 <memcpy@plt>
  3cb715:	4c 89 f9             	mov    %r15,%rcx
  3cb718:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3cb71f:	00 
  3cb720:	48 89 5c 24 30       	mov    %rbx,0x30(%rsp)
  3cb725:	41 c6 04 1e 00       	movb   $0x0,(%r14,%rbx,1)
  3cb72a:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3cb72f:	48 8b 5c 24 28       	mov    0x28(%rsp),%rbx
  3cb734:	48 39 cb             	cmp    %rcx,%rbx
  3cb737:	74 14                	je     3cb74d <_ZN5MCLoc20DoNormalUpdateActionEv+0x130d>
  3cb739:	48 89 5c 24 78       	mov    %rbx,0x78(%rsp)
  3cb73e:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3cb743:	48 89 84 24 88 00 00 	mov    %rax,0x88(%rsp)
  3cb74a:	00 
  3cb74b:	eb 0c                	jmp    3cb759 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1319>
  3cb74d:	f3 0f 6f 01          	movdqu (%rcx),%xmm0
  3cb751:	f3 41 0f 7f 07       	movdqu %xmm0,(%r15)
  3cb756:	4c 89 fb             	mov    %r15,%rbx
  3cb759:	4c 8b 74 24 30       	mov    0x30(%rsp),%r14
  3cb75e:	4c 89 b4 24 80 00 00 	mov    %r14,0x80(%rsp)
  3cb765:	00 
  3cb766:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cb76b:	48 c7 44 24 30 00 00 	movq   $0x0,0x30(%rsp)
  3cb772:	00 00 
  3cb774:	c6 44 24 38 00       	movb   $0x0,0x38(%rsp)
  3cb779:	48 c7 44 24 68 00 00 	movq   $0x0,0x68(%rsp)
  3cb780:	00 00 
  3cb782:	bf 28 00 00 00       	mov    $0x28,%edi
  3cb787:	e8 d4 ba de ff       	call   1b7260 <_Znwm@plt>
  3cb78c:	48 89 c1             	mov    %rax,%rcx
  3cb78f:	48 83 c1 10          	add    $0x10,%rcx
  3cb793:	48 89 08             	mov    %rcx,(%rax)
  3cb796:	4c 39 fb             	cmp    %r15,%rbx
  3cb799:	74 11                	je     3cb7ac <_ZN5MCLoc20DoNormalUpdateActionEv+0x136c>
  3cb79b:	48 89 18             	mov    %rbx,(%rax)
  3cb79e:	48 8b 8c 24 88 00 00 	mov    0x88(%rsp),%rcx
  3cb7a5:	00 
  3cb7a6:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3cb7aa:	eb 09                	jmp    3cb7b5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1375>
  3cb7ac:	f3 41 0f 6f 07       	movdqu (%r15),%xmm0
  3cb7b1:	f3 0f 7f 01          	movdqu %xmm0,(%rcx)
  3cb7b5:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3cb7ba:	48 c7 84 24 80 00 00 	movq   $0x0,0x80(%rsp)
  3cb7c1:	00 00 00 00 00 
  3cb7c6:	c6 84 24 88 00 00 00 	movb   $0x0,0x88(%rsp)
  3cb7cd:	00 
  3cb7ce:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3cb7d2:	48 89 44 24 58       	mov    %rax,0x58(%rsp)
  3cb7d7:	48 8d 05 72 9e 01 00 	lea    0x19e72(%rip),%rax        # 3e5650 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_28vEEE9_M_invokeERKSt9_Any_data>
  3cb7de:	48 89 44 24 70       	mov    %rax,0x70(%rsp)
  3cb7e3:	48 8d 05 46 a0 01 00 	lea    0x1a046(%rip),%rax        # 3e5830 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_28vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3cb7ea:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cb7ef:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3cb7f6:	00 00 
  3cb7f8:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3cb7fd:	48 8d 94 24 a0 00 00 	lea    0xa0(%rsp),%rdx
  3cb804:	00 
  3cb805:	48 8d 4c 24 58       	lea    0x58(%rsp),%rcx
  3cb80a:	31 f6                	xor    %esi,%esi
  3cb80c:	e8 7f 84 de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3cb811:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3cb816:	48 85 ff             	test   %rdi,%rdi
  3cb819:	4c 8b bc 24 c0 00 00 	mov    0xc0(%rsp),%r15
  3cb820:	00 
  3cb821:	74 17                	je     3cb83a <_ZN5MCLoc20DoNormalUpdateActionEv+0x13fa>
  3cb823:	48 8b 07             	mov    (%rdi),%rax
  3cb826:	48 8b 35 a3 e1 52 00 	mov    0x52e1a3(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3cb82d:	ff 50 20             	call   *0x20(%rax)
  3cb830:	48 89 c3             	mov    %rax,%rbx
  3cb833:	4c 8b 6c 24 50       	mov    0x50(%rsp),%r13
  3cb838:	eb 05                	jmp    3cb83f <_ZN5MCLoc20DoNormalUpdateActionEv+0x13ff>
  3cb83a:	45 31 ed             	xor    %r13d,%r13d
  3cb83d:	31 db                	xor    %ebx,%ebx
  3cb83f:	48 89 5c 24 48       	mov    %rbx,0x48(%rsp)
  3cb844:	4d 85 ed             	test   %r13,%r13
  3cb847:	74 17                	je     3cb860 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1420>
  3cb849:	48 83 3d df e2 52 00 	cmpq   $0x0,0x52e2df(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cb850:	00 
  3cb851:	74 08                	je     3cb85b <_ZN5MCLoc20DoNormalUpdateActionEv+0x141b>
  3cb853:	f0 41 83 45 08 01    	lock addl $0x1,0x8(%r13)
  3cb859:	eb 05                	jmp    3cb860 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1420>
  3cb85b:	41 83 45 08 01       	addl   $0x1,0x8(%r13)
  3cb860:	48 c7 84 24 b0 00 00 	movq   $0x0,0xb0(%rsp)
  3cb867:	00 00 00 00 00 
  3cb86c:	bf 10 00 00 00       	mov    $0x10,%edi
  3cb871:	e8 ea b9 de ff       	call   1b7260 <_Znwm@plt>
  3cb876:	48 89 18             	mov    %rbx,(%rax)
  3cb879:	4c 89 68 08          	mov    %r13,0x8(%rax)
  3cb87d:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3cb884:	00 
  3cb885:	48 8d 05 d4 a0 01 00 	lea    0x1a0d4(%rip),%rax        # 3e5960 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_28JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3cb88c:	48 89 84 24 b8 00 00 	mov    %rax,0xb8(%rsp)
  3cb893:	00 
  3cb894:	48 8d 05 f5 a0 01 00 	lea    0x1a0f5(%rip),%rax        # 3e5990 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_28JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3cb89b:	48 89 84 24 b0 00 00 	mov    %rax,0xb0(%rsp)
  3cb8a2:	00 
  3cb8a3:	49 8d 7c 24 08       	lea    0x8(%r12),%rdi
  3cb8a8:	48 8d b4 24 a0 00 00 	lea    0xa0(%rsp),%rsi
  3cb8af:	00 
  3cb8b0:	e8 4b 65 de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3cb8b5:	49 81 c4 c0 01 00 00 	add    $0x1c0,%r12
  3cb8bc:	4c 89 e7             	mov    %r12,%rdi
  3cb8bf:	e8 ac c8 de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3cb8c4:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3cb8c9:	48 8d bc 24 b0 03 00 	lea    0x3b0(%rsp),%rdi
  3cb8d0:	00 
  3cb8d1:	e8 fa d7 de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3cb8d6:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3cb8dd:	00 
  3cb8de:	48 85 c0             	test   %rax,%rax
  3cb8e1:	74 12                	je     3cb8f5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x14b5>
  3cb8e3:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3cb8ea:	00 
  3cb8eb:	ba 03 00 00 00       	mov    $0x3,%edx
  3cb8f0:	48 89 fe             	mov    %rdi,%rsi
  3cb8f3:	ff d0                	call   *%rax
  3cb8f5:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3cb8fa:	48 85 db             	test   %rbx,%rbx
  3cb8fd:	74 58                	je     3cb957 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1517>
  3cb8ff:	48 83 3d 29 e2 52 00 	cmpq   $0x0,0x52e229(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cb906:	00 
  3cb907:	74 11                	je     3cb91a <_ZN5MCLoc20DoNormalUpdateActionEv+0x14da>
  3cb909:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cb90e:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cb913:	83 f8 01             	cmp    $0x1,%eax
  3cb916:	74 10                	je     3cb928 <_ZN5MCLoc20DoNormalUpdateActionEv+0x14e8>
  3cb918:	eb 3d                	jmp    3cb957 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1517>
  3cb91a:	8b 43 08             	mov    0x8(%rbx),%eax
  3cb91d:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cb920:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cb923:	83 f8 01             	cmp    $0x1,%eax
  3cb926:	75 2f                	jne    3cb957 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1517>
  3cb928:	48 8b 03             	mov    (%rbx),%rax
  3cb92b:	48 89 df             	mov    %rbx,%rdi
  3cb92e:	ff 50 10             	call   *0x10(%rax)
  3cb931:	48 83 3d f7 e1 52 00 	cmpq   $0x0,0x52e1f7(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cb938:	00 
  3cb939:	0f 84 fe 1a 00 00    	je     3cd43d <_ZN5MCLoc20DoNormalUpdateActionEv+0x2ffd>
  3cb93f:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cb944:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cb949:	83 f8 01             	cmp    $0x1,%eax
  3cb94c:	75 09                	jne    3cb957 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1517>
  3cb94e:	48 8b 03             	mov    (%rbx),%rax
  3cb951:	48 89 df             	mov    %rbx,%rdi
  3cb954:	ff 50 18             	call   *0x18(%rax)
  3cb957:	48 8b 44 24 68       	mov    0x68(%rsp),%rax
  3cb95c:	48 85 c0             	test   %rax,%rax
  3cb95f:	74 0f                	je     3cb970 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1530>
  3cb961:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3cb966:	ba 03 00 00 00       	mov    $0x3,%edx
  3cb96b:	48 89 fe             	mov    %rdi,%rsi
  3cb96e:	ff d0                	call   *%rax
  3cb970:	48 8b 9c 24 b8 03 00 	mov    0x3b8(%rsp),%rbx
  3cb977:	00 
  3cb978:	48 85 db             	test   %rbx,%rbx
  3cb97b:	74 58                	je     3cb9d5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1595>
  3cb97d:	48 83 3d ab e1 52 00 	cmpq   $0x0,0x52e1ab(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cb984:	00 
  3cb985:	74 11                	je     3cb998 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1558>
  3cb987:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cb98c:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cb991:	83 f8 01             	cmp    $0x1,%eax
  3cb994:	74 10                	je     3cb9a6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1566>
  3cb996:	eb 3d                	jmp    3cb9d5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1595>
  3cb998:	8b 43 08             	mov    0x8(%rbx),%eax
  3cb99b:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cb99e:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cb9a1:	83 f8 01             	cmp    $0x1,%eax
  3cb9a4:	75 2f                	jne    3cb9d5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1595>
  3cb9a6:	48 8b 03             	mov    (%rbx),%rax
  3cb9a9:	48 89 df             	mov    %rbx,%rdi
  3cb9ac:	ff 50 10             	call   *0x10(%rax)
  3cb9af:	48 83 3d 79 e1 52 00 	cmpq   $0x0,0x52e179(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cb9b6:	00 
  3cb9b7:	0f 84 3e 1c 00 00    	je     3cd5fb <_ZN5MCLoc20DoNormalUpdateActionEv+0x31bb>
  3cb9bd:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cb9c2:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cb9c7:	83 f8 01             	cmp    $0x1,%eax
  3cb9ca:	75 09                	jne    3cb9d5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1595>
  3cb9cc:	48 8b 03             	mov    (%rbx),%rax
  3cb9cf:	48 89 df             	mov    %rbx,%rdi
  3cb9d2:	ff 50 18             	call   *0x18(%rax)
  3cb9d5:	48 8b 7c 24 28       	mov    0x28(%rsp),%rdi
  3cb9da:	48 8d 44 24 38       	lea    0x38(%rsp),%rax
  3cb9df:	48 39 c7             	cmp    %rax,%rdi
  3cb9e2:	74 05                	je     3cb9e9 <_ZN5MCLoc20DoNormalUpdateActionEv+0x15a9>
  3cb9e4:	e8 07 3f de ff       	call   1af8f0 <_ZdlPv@plt>
  3cb9e9:	48 8b bc 24 c8 00 00 	mov    0xc8(%rsp),%rdi
  3cb9f0:	00 
  3cb9f1:	48 8d 84 24 d8 00 00 	lea    0xd8(%rsp),%rax
  3cb9f8:	00 
  3cb9f9:	48 39 c7             	cmp    %rax,%rdi
  3cb9fc:	74 05                	je     3cba03 <_ZN5MCLoc20DoNormalUpdateActionEv+0x15c3>
  3cb9fe:	e8 ed 3e de ff       	call   1af8f0 <_ZdlPv@plt>
  3cba03:	48 8b 1d be f0 52 00 	mov    0x52f0be(%rip),%rbx        # 8faac8 <_ZTTNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cba0a:	48 8b 03             	mov    (%rbx),%rax
  3cba0d:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cba14:	00 
  3cba15:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  3cba19:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cba1d:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cba24:	00 
  3cba25:	48 8b 43 48          	mov    0x48(%rbx),%rax
  3cba29:	48 89 84 24 28 01 00 	mov    %rax,0x128(%rsp)
  3cba30:	00 
  3cba31:	48 8b 05 b8 b8 52 00 	mov    0x52b8b8(%rip),%rax        # 8f72f0 <_ZTVNSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cba38:	48 83 c0 10          	add    $0x10,%rax
  3cba3c:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cba43:	00 
  3cba44:	48 8b bc 24 78 01 00 	mov    0x178(%rsp),%rdi
  3cba4b:	00 
  3cba4c:	48 8d 84 24 88 01 00 	lea    0x188(%rsp),%rax
  3cba53:	00 
  3cba54:	48 39 c7             	cmp    %rax,%rdi
  3cba57:	74 05                	je     3cba5e <_ZN5MCLoc20DoNormalUpdateActionEv+0x161e>
  3cba59:	e8 92 3e de ff       	call   1af8f0 <_ZdlPv@plt>
  3cba5e:	48 8b 05 eb cf 52 00 	mov    0x52cfeb(%rip),%rax        # 8f8a50 <_ZTVSt15basic_streambufIcSt11char_traitsIcEE@GLIBCXX_3.4>
  3cba65:	48 83 c0 10          	add    $0x10,%rax
  3cba69:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cba70:	00 
  3cba71:	48 8d bc 24 68 01 00 	lea    0x168(%rsp),%rdi
  3cba78:	00 
  3cba79:	e8 82 80 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3cba7e:	48 8b 43 10          	mov    0x10(%rbx),%rax
  3cba82:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  3cba86:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cba8d:	00 
  3cba8e:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cba92:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cba99:	00 
  3cba9a:	48 c7 84 24 20 01 00 	movq   $0x0,0x120(%rsp)
  3cbaa1:	00 00 00 00 00 
  3cbaa6:	48 8d bc 24 98 01 00 	lea    0x198(%rsp),%rdi
  3cbaad:	00 
  3cbaae:	e8 0d cc de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3cbab3:	49 8b bf a8 d2 d0 03 	mov    0x3d0d2a8(%r15),%rdi
  3cbaba:	49 8b 87 88 c7 d0 03 	mov    0x3d0c788(%r15),%rax
  3cbac1:	66 48 0f 6e c0       	movq   %rax,%xmm0
  3cbac6:	31 c0                	xor    %eax,%eax
  3cbac8:	31 c9                	xor    %ecx,%ecx
  3cbaca:	41 86 8f 20 c7 d0 03 	xchg   %cl,0x3d0c720(%r15)
  3cbad1:	49 8b 8f 58 c8 d0 03 	mov    0x3d0c858(%r15),%rcx
  3cbad8:	66 48 0f 6e c9       	movq   %rcx,%xmm1
  3cbadd:	41 86 87 f0 c7 d0 03 	xchg   %al,0x3d0c7f0(%r15)
  3cbae4:	48 8b 84 24 d8 02 00 	mov    0x2d8(%rsp),%rax
  3cbaeb:	00 
  3cbaec:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
  3cbaf1:	66 0f 10 94 24 c8 02 	movupd 0x2c8(%rsp),%xmm2
  3cbaf8:	00 00 
  3cbafa:	66 0f 11 14 24       	movupd %xmm2,(%rsp)
  3cbaff:	e8 9c a7 de ff       	call   1b62a0 <_ZN3rbk9algorithm16MCLMotionModel2D18setExtraMoveParamsEddNS0_10StateVar2DE@plt>
  3cbb04:	48 8d 94 24 a0 02 00 	lea    0x2a0(%rsp),%rdx
  3cbb0b:	00 
  3cbb0c:	be 03 00 00 00       	mov    $0x3,%esi
  3cbb11:	48 8b bc 24 f8 00 00 	mov    0xf8(%rsp),%rdi
  3cbb18:	00 
  3cbb19:	e8 d2 32 de ff       	call   1aedf0 <_ZN3rbk9algorithm16ParticleFilter2D15ParticlesActionENS1_9Whats2RunERSt6vectorIdSaIdEE@plt>
  3cbb1e:	41 80 bf f9 19 00 00 	cmpb   $0x0,0x19f9(%r15)
  3cbb25:	00 
  3cbb26:	0f 84 08 0a 00 00    	je     3cc534 <_ZN5MCLoc20DoNormalUpdateActionEv+0x20f4>
  3cbb2c:	48 8d bc 24 18 01 00 	lea    0x118(%rsp),%rdi
  3cbb33:	00 
  3cbb34:	be 18 00 00 00       	mov    $0x18,%esi
  3cbb39:	e8 d2 92 de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3cbb3e:	48 8d bc 24 28 01 00 	lea    0x128(%rsp),%rdi
  3cbb45:	00 
  3cbb46:	48 8d 35 b6 8a 1f 00 	lea    0x1f8ab6(%rip),%rsi        # 5c4603 <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc15SetGnssParticleERKNS_8protocol12Message_GNSSEE4$_43JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x373>
  3cbb4d:	ba 24 00 00 00       	mov    $0x24,%edx
  3cbb52:	e8 99 4f de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3cbb57:	48 8d b4 24 30 01 00 	lea    0x130(%rsp),%rsi
  3cbb5e:	00 
  3cbb5f:	48 8d bc 24 c8 00 00 	lea    0xc8(%rsp),%rdi
  3cbb66:	00 
  3cbb67:	e8 f4 90 de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3cbb6c:	e8 6f bd de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3cbb71:	49 89 c4             	mov    %rax,%r12
  3cbb74:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cbb79:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cbb7e:	4c 8b ac 24 c8 00 00 	mov    0xc8(%rsp),%r13
  3cbb85:	00 
  3cbb86:	48 8b 9c 24 d0 00 00 	mov    0xd0(%rsp),%rbx
  3cbb8d:	00 
  3cbb8e:	4d 85 ed             	test   %r13,%r13
  3cbb91:	75 09                	jne    3cbb9c <_ZN5MCLoc20DoNormalUpdateActionEv+0x175c>
  3cbb93:	48 85 db             	test   %rbx,%rbx
  3cbb96:	0f 85 27 20 00 00    	jne    3cdbc3 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3783>
  3cbb9c:	49 89 ce             	mov    %rcx,%r14
  3cbb9f:	48 83 fb 10          	cmp    $0x10,%rbx
  3cbba3:	72 24                	jb     3cbbc9 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1789>
  3cbba5:	48 85 db             	test   %rbx,%rbx
  3cbba8:	0f 88 40 20 00 00    	js     3cdbee <_ZN5MCLoc20DoNormalUpdateActionEv+0x37ae>
  3cbbae:	48 8d 7b 01          	lea    0x1(%rbx),%rdi
  3cbbb2:	e8 a9 b6 de ff       	call   1b7260 <_Znwm@plt>
  3cbbb7:	49 89 c6             	mov    %rax,%r14
  3cbbba:	4c 89 74 24 28       	mov    %r14,0x28(%rsp)
  3cbbbf:	48 89 5c 24 38       	mov    %rbx,0x38(%rsp)
  3cbbc4:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cbbc9:	48 85 db             	test   %rbx,%rbx
  3cbbcc:	74 22                	je     3cbbf0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x17b0>
  3cbbce:	48 83 fb 01          	cmp    $0x1,%rbx
  3cbbd2:	75 09                	jne    3cbbdd <_ZN5MCLoc20DoNormalUpdateActionEv+0x179d>
  3cbbd4:	41 8a 45 00          	mov    0x0(%r13),%al
  3cbbd8:	41 88 06             	mov    %al,(%r14)
  3cbbdb:	eb 13                	jmp    3cbbf0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x17b0>
  3cbbdd:	4c 89 f7             	mov    %r14,%rdi
  3cbbe0:	4c 89 ee             	mov    %r13,%rsi
  3cbbe3:	48 89 da             	mov    %rbx,%rdx
  3cbbe6:	e8 95 b3 de ff       	call   1b6f80 <memcpy@plt>
  3cbbeb:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cbbf0:	48 89 5c 24 30       	mov    %rbx,0x30(%rsp)
  3cbbf5:	41 c6 04 1e 00       	movb   $0x0,(%r14,%rbx,1)
  3cbbfa:	4c 8d ac 24 88 00 00 	lea    0x88(%rsp),%r13
  3cbc01:	00 
  3cbc02:	4c 89 6c 24 78       	mov    %r13,0x78(%rsp)
  3cbc07:	48 8b 5c 24 28       	mov    0x28(%rsp),%rbx
  3cbc0c:	48 39 cb             	cmp    %rcx,%rbx
  3cbc0f:	74 14                	je     3cbc25 <_ZN5MCLoc20DoNormalUpdateActionEv+0x17e5>
  3cbc11:	48 89 5c 24 78       	mov    %rbx,0x78(%rsp)
  3cbc16:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3cbc1b:	48 89 84 24 88 00 00 	mov    %rax,0x88(%rsp)
  3cbc22:	00 
  3cbc23:	eb 0d                	jmp    3cbc32 <_ZN5MCLoc20DoNormalUpdateActionEv+0x17f2>
  3cbc25:	f3 0f 6f 01          	movdqu (%rcx),%xmm0
  3cbc29:	f3 41 0f 7f 45 00    	movdqu %xmm0,0x0(%r13)
  3cbc2f:	4c 89 eb             	mov    %r13,%rbx
  3cbc32:	4c 8b 74 24 30       	mov    0x30(%rsp),%r14
  3cbc37:	4c 89 b4 24 80 00 00 	mov    %r14,0x80(%rsp)
  3cbc3e:	00 
  3cbc3f:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cbc44:	48 c7 44 24 30 00 00 	movq   $0x0,0x30(%rsp)
  3cbc4b:	00 00 
  3cbc4d:	c6 44 24 38 00       	movb   $0x0,0x38(%rsp)
  3cbc52:	48 c7 44 24 68 00 00 	movq   $0x0,0x68(%rsp)
  3cbc59:	00 00 
  3cbc5b:	bf 28 00 00 00       	mov    $0x28,%edi
  3cbc60:	e8 fb b5 de ff       	call   1b7260 <_Znwm@plt>
  3cbc65:	48 89 c1             	mov    %rax,%rcx
  3cbc68:	48 83 c1 10          	add    $0x10,%rcx
  3cbc6c:	48 89 08             	mov    %rcx,(%rax)
  3cbc6f:	4c 39 eb             	cmp    %r13,%rbx
  3cbc72:	74 11                	je     3cbc85 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1845>
  3cbc74:	48 89 18             	mov    %rbx,(%rax)
  3cbc77:	48 8b 8c 24 88 00 00 	mov    0x88(%rsp),%rcx
  3cbc7e:	00 
  3cbc7f:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3cbc83:	eb 0a                	jmp    3cbc8f <_ZN5MCLoc20DoNormalUpdateActionEv+0x184f>
  3cbc85:	f3 41 0f 6f 45 00    	movdqu 0x0(%r13),%xmm0
  3cbc8b:	f3 0f 7f 01          	movdqu %xmm0,(%rcx)
  3cbc8f:	4c 89 6c 24 78       	mov    %r13,0x78(%rsp)
  3cbc94:	48 c7 84 24 80 00 00 	movq   $0x0,0x80(%rsp)
  3cbc9b:	00 00 00 00 00 
  3cbca0:	c6 84 24 88 00 00 00 	movb   $0x0,0x88(%rsp)
  3cbca7:	00 
  3cbca8:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3cbcac:	48 89 44 24 58       	mov    %rax,0x58(%rsp)
  3cbcb1:	48 8d 05 b8 a6 01 00 	lea    0x1a6b8(%rip),%rax        # 3e6370 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_31vEEE9_M_invokeERKSt9_Any_data>
  3cbcb8:	48 89 44 24 70       	mov    %rax,0x70(%rsp)
  3cbcbd:	48 8d 05 8c a8 01 00 	lea    0x1a88c(%rip),%rax        # 3e6550 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_31vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3cbcc4:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cbcc9:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3cbcd0:	00 00 
  3cbcd2:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3cbcd7:	48 8d 94 24 a0 00 00 	lea    0xa0(%rsp),%rdx
  3cbcde:	00 
  3cbcdf:	48 8d 4c 24 58       	lea    0x58(%rsp),%rcx
  3cbce4:	31 f6                	xor    %esi,%esi
  3cbce6:	e8 a5 7f de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3cbceb:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3cbcf0:	48 85 ff             	test   %rdi,%rdi
  3cbcf3:	74 17                	je     3cbd0c <_ZN5MCLoc20DoNormalUpdateActionEv+0x18cc>
  3cbcf5:	48 8b 07             	mov    (%rdi),%rax
  3cbcf8:	48 8b 35 d1 dc 52 00 	mov    0x52dcd1(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3cbcff:	ff 50 20             	call   *0x20(%rax)
  3cbd02:	48 89 c3             	mov    %rax,%rbx
  3cbd05:	4c 8b 6c 24 50       	mov    0x50(%rsp),%r13
  3cbd0a:	eb 05                	jmp    3cbd11 <_ZN5MCLoc20DoNormalUpdateActionEv+0x18d1>
  3cbd0c:	45 31 ed             	xor    %r13d,%r13d
  3cbd0f:	31 db                	xor    %ebx,%ebx
  3cbd11:	48 89 5c 24 48       	mov    %rbx,0x48(%rsp)
  3cbd16:	4d 85 ed             	test   %r13,%r13
  3cbd19:	74 17                	je     3cbd32 <_ZN5MCLoc20DoNormalUpdateActionEv+0x18f2>
  3cbd1b:	48 83 3d 0d de 52 00 	cmpq   $0x0,0x52de0d(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cbd22:	00 
  3cbd23:	74 08                	je     3cbd2d <_ZN5MCLoc20DoNormalUpdateActionEv+0x18ed>
  3cbd25:	f0 41 83 45 08 01    	lock addl $0x1,0x8(%r13)
  3cbd2b:	eb 05                	jmp    3cbd32 <_ZN5MCLoc20DoNormalUpdateActionEv+0x18f2>
  3cbd2d:	41 83 45 08 01       	addl   $0x1,0x8(%r13)
  3cbd32:	48 c7 84 24 b0 00 00 	movq   $0x0,0xb0(%rsp)
  3cbd39:	00 00 00 00 00 
  3cbd3e:	bf 10 00 00 00       	mov    $0x10,%edi
  3cbd43:	e8 18 b5 de ff       	call   1b7260 <_Znwm@plt>
  3cbd48:	48 89 18             	mov    %rbx,(%rax)
  3cbd4b:	4c 89 68 08          	mov    %r13,0x8(%rax)
  3cbd4f:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3cbd56:	00 
  3cbd57:	48 8d 05 22 a9 01 00 	lea    0x1a922(%rip),%rax        # 3e6680 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_31JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3cbd5e:	48 89 84 24 b8 00 00 	mov    %rax,0xb8(%rsp)
  3cbd65:	00 
  3cbd66:	48 8d 05 43 a9 01 00 	lea    0x1a943(%rip),%rax        # 3e66b0 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_31JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3cbd6d:	48 89 84 24 b0 00 00 	mov    %rax,0xb0(%rsp)
  3cbd74:	00 
  3cbd75:	49 8d 7c 24 08       	lea    0x8(%r12),%rdi
  3cbd7a:	48 8d b4 24 a0 00 00 	lea    0xa0(%rsp),%rsi
  3cbd81:	00 
  3cbd82:	e8 79 60 de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3cbd87:	49 81 c4 c0 01 00 00 	add    $0x1c0,%r12
  3cbd8e:	4c 89 e7             	mov    %r12,%rdi
  3cbd91:	e8 da c3 de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3cbd96:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3cbd9b:	48 8d bc 24 80 03 00 	lea    0x380(%rsp),%rdi
  3cbda2:	00 
  3cbda3:	e8 28 d3 de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3cbda8:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3cbdaf:	00 
  3cbdb0:	48 85 c0             	test   %rax,%rax
  3cbdb3:	74 12                	je     3cbdc7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1987>
  3cbdb5:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3cbdbc:	00 
  3cbdbd:	ba 03 00 00 00       	mov    $0x3,%edx
  3cbdc2:	48 89 fe             	mov    %rdi,%rsi
  3cbdc5:	ff d0                	call   *%rax
  3cbdc7:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3cbdcc:	48 85 db             	test   %rbx,%rbx
  3cbdcf:	74 64                	je     3cbe35 <_ZN5MCLoc20DoNormalUpdateActionEv+0x19f5>
  3cbdd1:	48 83 3d 57 dd 52 00 	cmpq   $0x0,0x52dd57(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cbdd8:	00 
  3cbdd9:	74 11                	je     3cbdec <_ZN5MCLoc20DoNormalUpdateActionEv+0x19ac>
  3cbddb:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cbde0:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cbde5:	83 f8 01             	cmp    $0x1,%eax
  3cbde8:	74 10                	je     3cbdfa <_ZN5MCLoc20DoNormalUpdateActionEv+0x19ba>
  3cbdea:	eb 49                	jmp    3cbe35 <_ZN5MCLoc20DoNormalUpdateActionEv+0x19f5>
  3cbdec:	8b 43 08             	mov    0x8(%rbx),%eax
  3cbdef:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cbdf2:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cbdf5:	83 f8 01             	cmp    $0x1,%eax
  3cbdf8:	75 3b                	jne    3cbe35 <_ZN5MCLoc20DoNormalUpdateActionEv+0x19f5>
  3cbdfa:	48 8b 03             	mov    (%rbx),%rax
  3cbdfd:	48 89 df             	mov    %rbx,%rdi
  3cbe00:	ff 50 10             	call   *0x10(%rax)
  3cbe03:	48 83 3d 25 dd 52 00 	cmpq   $0x0,0x52dd25(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cbe0a:	00 
  3cbe0b:	74 11                	je     3cbe1e <_ZN5MCLoc20DoNormalUpdateActionEv+0x19de>
  3cbe0d:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cbe12:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cbe17:	83 f8 01             	cmp    $0x1,%eax
  3cbe1a:	74 10                	je     3cbe2c <_ZN5MCLoc20DoNormalUpdateActionEv+0x19ec>
  3cbe1c:	eb 17                	jmp    3cbe35 <_ZN5MCLoc20DoNormalUpdateActionEv+0x19f5>
  3cbe1e:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cbe21:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cbe24:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cbe27:	83 f8 01             	cmp    $0x1,%eax
  3cbe2a:	75 09                	jne    3cbe35 <_ZN5MCLoc20DoNormalUpdateActionEv+0x19f5>
  3cbe2c:	48 8b 03             	mov    (%rbx),%rax
  3cbe2f:	48 89 df             	mov    %rbx,%rdi
  3cbe32:	ff 50 18             	call   *0x18(%rax)
  3cbe35:	48 8b 44 24 68       	mov    0x68(%rsp),%rax
  3cbe3a:	48 85 c0             	test   %rax,%rax
  3cbe3d:	74 0f                	je     3cbe4e <_ZN5MCLoc20DoNormalUpdateActionEv+0x1a0e>
  3cbe3f:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3cbe44:	ba 03 00 00 00       	mov    $0x3,%edx
  3cbe49:	48 89 fe             	mov    %rdi,%rsi
  3cbe4c:	ff d0                	call   *%rax
  3cbe4e:	48 8b 9c 24 88 03 00 	mov    0x388(%rsp),%rbx
  3cbe55:	00 
  3cbe56:	48 85 db             	test   %rbx,%rbx
  3cbe59:	74 64                	je     3cbebf <_ZN5MCLoc20DoNormalUpdateActionEv+0x1a7f>
  3cbe5b:	48 83 3d cd dc 52 00 	cmpq   $0x0,0x52dccd(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cbe62:	00 
  3cbe63:	74 11                	je     3cbe76 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1a36>
  3cbe65:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cbe6a:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cbe6f:	83 f8 01             	cmp    $0x1,%eax
  3cbe72:	74 10                	je     3cbe84 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1a44>
  3cbe74:	eb 49                	jmp    3cbebf <_ZN5MCLoc20DoNormalUpdateActionEv+0x1a7f>
  3cbe76:	8b 43 08             	mov    0x8(%rbx),%eax
  3cbe79:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cbe7c:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cbe7f:	83 f8 01             	cmp    $0x1,%eax
  3cbe82:	75 3b                	jne    3cbebf <_ZN5MCLoc20DoNormalUpdateActionEv+0x1a7f>
  3cbe84:	48 8b 03             	mov    (%rbx),%rax
  3cbe87:	48 89 df             	mov    %rbx,%rdi
  3cbe8a:	ff 50 10             	call   *0x10(%rax)
  3cbe8d:	48 83 3d 9b dc 52 00 	cmpq   $0x0,0x52dc9b(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cbe94:	00 
  3cbe95:	74 11                	je     3cbea8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1a68>
  3cbe97:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cbe9c:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cbea1:	83 f8 01             	cmp    $0x1,%eax
  3cbea4:	74 10                	je     3cbeb6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1a76>
  3cbea6:	eb 17                	jmp    3cbebf <_ZN5MCLoc20DoNormalUpdateActionEv+0x1a7f>
  3cbea8:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cbeab:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cbeae:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cbeb1:	83 f8 01             	cmp    $0x1,%eax
  3cbeb4:	75 09                	jne    3cbebf <_ZN5MCLoc20DoNormalUpdateActionEv+0x1a7f>
  3cbeb6:	48 8b 03             	mov    (%rbx),%rax
  3cbeb9:	48 89 df             	mov    %rbx,%rdi
  3cbebc:	ff 50 18             	call   *0x18(%rax)
  3cbebf:	48 8b 7c 24 28       	mov    0x28(%rsp),%rdi
  3cbec4:	48 8d 44 24 38       	lea    0x38(%rsp),%rax
  3cbec9:	48 39 c7             	cmp    %rax,%rdi
  3cbecc:	74 05                	je     3cbed3 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1a93>
  3cbece:	e8 1d 3a de ff       	call   1af8f0 <_ZdlPv@plt>
  3cbed3:	48 8b bc 24 c8 00 00 	mov    0xc8(%rsp),%rdi
  3cbeda:	00 
  3cbedb:	48 8d 84 24 d8 00 00 	lea    0xd8(%rsp),%rax
  3cbee2:	00 
  3cbee3:	48 39 c7             	cmp    %rax,%rdi
  3cbee6:	74 05                	je     3cbeed <_ZN5MCLoc20DoNormalUpdateActionEv+0x1aad>
  3cbee8:	e8 03 3a de ff       	call   1af8f0 <_ZdlPv@plt>
  3cbeed:	48 8b 1d d4 eb 52 00 	mov    0x52ebd4(%rip),%rbx        # 8faac8 <_ZTTNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cbef4:	48 8b 03             	mov    (%rbx),%rax
  3cbef7:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cbefe:	00 
  3cbeff:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  3cbf03:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  3cbf0a:	00 
  3cbf0b:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cbf0f:	48 89 8c 24 f0 00 00 	mov    %rcx,0xf0(%rsp)
  3cbf16:	00 
  3cbf17:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cbf1e:	00 
  3cbf1f:	48 8b 43 48          	mov    0x48(%rbx),%rax
  3cbf23:	48 89 84 24 c0 00 00 	mov    %rax,0xc0(%rsp)
  3cbf2a:	00 
  3cbf2b:	48 89 84 24 28 01 00 	mov    %rax,0x128(%rsp)
  3cbf32:	00 
  3cbf33:	48 8b 05 b6 b3 52 00 	mov    0x52b3b6(%rip),%rax        # 8f72f0 <_ZTVNSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cbf3a:	48 83 c0 10          	add    $0x10,%rax
  3cbf3e:	48 89 84 24 10 01 00 	mov    %rax,0x110(%rsp)
  3cbf45:	00 
  3cbf46:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cbf4d:	00 
  3cbf4e:	48 8b bc 24 78 01 00 	mov    0x178(%rsp),%rdi
  3cbf55:	00 
  3cbf56:	48 8d 84 24 88 01 00 	lea    0x188(%rsp),%rax
  3cbf5d:	00 
  3cbf5e:	48 39 c7             	cmp    %rax,%rdi
  3cbf61:	74 05                	je     3cbf68 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1b28>
  3cbf63:	e8 88 39 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cbf68:	4c 8b 2d e1 ca 52 00 	mov    0x52cae1(%rip),%r13        # 8f8a50 <_ZTVSt15basic_streambufIcSt11char_traitsIcEE@GLIBCXX_3.4>
  3cbf6f:	49 83 c5 10          	add    $0x10,%r13
  3cbf73:	4c 89 ac 24 30 01 00 	mov    %r13,0x130(%rsp)
  3cbf7a:	00 
  3cbf7b:	48 8d bc 24 68 01 00 	lea    0x168(%rsp),%rdi
  3cbf82:	00 
  3cbf83:	e8 78 7b de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3cbf88:	4c 8b 63 10          	mov    0x10(%rbx),%r12
  3cbf8c:	4c 8b 73 18          	mov    0x18(%rbx),%r14
  3cbf90:	4c 89 a4 24 18 01 00 	mov    %r12,0x118(%rsp)
  3cbf97:	00 
  3cbf98:	49 8b 44 24 e8       	mov    -0x18(%r12),%rax
  3cbf9d:	4c 89 b4 04 18 01 00 	mov    %r14,0x118(%rsp,%rax,1)
  3cbfa4:	00 
  3cbfa5:	48 c7 84 24 20 01 00 	movq   $0x0,0x120(%rsp)
  3cbfac:	00 00 00 00 00 
  3cbfb1:	48 8d bc 24 98 01 00 	lea    0x198(%rsp),%rdi
  3cbfb8:	00 
  3cbfb9:	e8 02 c7 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3cbfbe:	41 c6 87 f9 19 00 00 	movb   $0x0,0x19f9(%r15)
  3cbfc5:	00 
  3cbfc6:	49 8b bf a8 d2 d0 03 	mov    0x3d0d2a8(%r15),%rdi
  3cbfcd:	f2 0f 10 0d c3 69 19 	movsd  0x1969c3(%rip),%xmm1        # 562998 <_ZTS11errorLogger+0x4e>
  3cbfd4:	00 
  3cbfd5:	f2 41 0f 10 87 10 1a 	movsd  0x1a10(%r15),%xmm0
  3cbfdc:	00 00 
  3cbfde:	f2 0f 59 c1          	mulsd  %xmm1,%xmm0
  3cbfe2:	f2 41 0f 59 8f 18 1a 	mulsd  0x1a18(%r15),%xmm1
  3cbfe9:	00 00 
  3cbfeb:	e8 f0 46 de ff       	call   1b06e0 <_ZN3rbk9algorithm16MCLMotionModel2D18setLaserMoveOffsetEdd@plt>
  3cbff0:	48 8d 94 24 a0 02 00 	lea    0x2a0(%rsp),%rdx
  3cbff7:	00 
  3cbff8:	be 04 00 00 00       	mov    $0x4,%esi
  3cbffd:	48 8b bc 24 f8 00 00 	mov    0xf8(%rsp),%rdi
  3cc004:	00 
  3cc005:	e8 e6 2d de ff       	call   1aedf0 <_ZN3rbk9algorithm16ParticleFilter2D15ParticlesActionENS1_9Whats2RunERSt6vectorIdSaIdEE@plt>
  3cc00a:	48 8d bc 24 18 01 00 	lea    0x118(%rsp),%rdi
  3cc011:	00 
  3cc012:	be 18 00 00 00       	mov    $0x18,%esi
  3cc017:	e8 f4 8d de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3cc01c:	48 8d 9c 24 28 01 00 	lea    0x128(%rsp),%rbx
  3cc023:	00 
  3cc024:	48 8d 35 fd 85 1f 00 	lea    0x1f85fd(%rip),%rsi        # 5c4628 <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc15SetGnssParticleERKNS_8protocol12Message_GNSSEE4$_43JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x398>
  3cc02b:	ba 08 00 00 00       	mov    $0x8,%edx
  3cc030:	48 89 df             	mov    %rbx,%rdi
  3cc033:	4c 89 b4 24 e8 02 00 	mov    %r14,0x2e8(%rsp)
  3cc03a:	00 
  3cc03b:	4c 89 a4 24 e0 02 00 	mov    %r12,0x2e0(%rsp)
  3cc042:	00 
  3cc043:	4c 89 ac 24 f0 02 00 	mov    %r13,0x2f0(%rsp)
  3cc04a:	00 
  3cc04b:	e8 a0 4a de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3cc050:	f2 41 0f 10 87 10 1a 	movsd  0x1a10(%r15),%xmm0
  3cc057:	00 00 
  3cc059:	48 89 df             	mov    %rbx,%rdi
  3cc05c:	e8 bf 9c de ff       	call   1b5d20 <_ZNSo9_M_insertIdEERSoT_@plt>
  3cc061:	48 89 c3             	mov    %rax,%rbx
  3cc064:	48 8d 35 23 ab 21 00 	lea    0x21ab23(%rip),%rsi        # 5e6b8e <_ZTSZN3rbk6Logger6Thread11move2threadIZN20seertag_localization14SeerTagGetPoseERNS_8protocol27Message_RecognizeResultListERNS_9algorithm10StateVar2DEE4$_37JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x18e>
  3cc06b:	ba 01 00 00 00       	mov    $0x1,%edx
  3cc070:	48 89 df             	mov    %rbx,%rdi
  3cc073:	e8 78 4a de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3cc078:	f2 41 0f 10 87 18 1a 	movsd  0x1a18(%r15),%xmm0
  3cc07f:	00 00 
  3cc081:	48 89 df             	mov    %rbx,%rdi
  3cc084:	e8 97 9c de ff       	call   1b5d20 <_ZNSo9_M_insertIdEERSoT_@plt>
  3cc089:	48 8d b4 24 30 01 00 	lea    0x130(%rsp),%rsi
  3cc090:	00 
  3cc091:	48 8d bc 24 c8 00 00 	lea    0xc8(%rsp),%rdi
  3cc098:	00 
  3cc099:	e8 c2 8b de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3cc09e:	e8 3d b8 de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3cc0a3:	49 89 c4             	mov    %rax,%r12
  3cc0a6:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cc0ab:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cc0b0:	4c 8b ac 24 c8 00 00 	mov    0xc8(%rsp),%r13
  3cc0b7:	00 
  3cc0b8:	48 8b 9c 24 d0 00 00 	mov    0xd0(%rsp),%rbx
  3cc0bf:	00 
  3cc0c0:	4d 85 ed             	test   %r13,%r13
  3cc0c3:	75 09                	jne    3cc0ce <_ZN5MCLoc20DoNormalUpdateActionEv+0x1c8e>
  3cc0c5:	48 85 db             	test   %rbx,%rbx
  3cc0c8:	0f 85 01 1b 00 00    	jne    3cdbcf <_ZN5MCLoc20DoNormalUpdateActionEv+0x378f>
  3cc0ce:	49 89 ce             	mov    %rcx,%r14
  3cc0d1:	48 83 fb 10          	cmp    $0x10,%rbx
  3cc0d5:	72 24                	jb     3cc0fb <_ZN5MCLoc20DoNormalUpdateActionEv+0x1cbb>
  3cc0d7:	48 85 db             	test   %rbx,%rbx
  3cc0da:	0f 88 1a 1b 00 00    	js     3cdbfa <_ZN5MCLoc20DoNormalUpdateActionEv+0x37ba>
  3cc0e0:	48 8d 7b 01          	lea    0x1(%rbx),%rdi
  3cc0e4:	e8 77 b1 de ff       	call   1b7260 <_Znwm@plt>
  3cc0e9:	49 89 c6             	mov    %rax,%r14
  3cc0ec:	4c 89 74 24 28       	mov    %r14,0x28(%rsp)
  3cc0f1:	48 89 5c 24 38       	mov    %rbx,0x38(%rsp)
  3cc0f6:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cc0fb:	48 85 db             	test   %rbx,%rbx
  3cc0fe:	74 22                	je     3cc122 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1ce2>
  3cc100:	48 83 fb 01          	cmp    $0x1,%rbx
  3cc104:	75 09                	jne    3cc10f <_ZN5MCLoc20DoNormalUpdateActionEv+0x1ccf>
  3cc106:	41 8a 45 00          	mov    0x0(%r13),%al
  3cc10a:	41 88 06             	mov    %al,(%r14)
  3cc10d:	eb 13                	jmp    3cc122 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1ce2>
  3cc10f:	4c 89 f7             	mov    %r14,%rdi
  3cc112:	4c 89 ee             	mov    %r13,%rsi
  3cc115:	48 89 da             	mov    %rbx,%rdx
  3cc118:	e8 63 ae de ff       	call   1b6f80 <memcpy@plt>
  3cc11d:	48 8d 4c 24 38       	lea    0x38(%rsp),%rcx
  3cc122:	48 89 5c 24 30       	mov    %rbx,0x30(%rsp)
  3cc127:	41 c6 04 1e 00       	movb   $0x0,(%r14,%rbx,1)
  3cc12c:	4c 8d ac 24 88 00 00 	lea    0x88(%rsp),%r13
  3cc133:	00 
  3cc134:	4c 89 6c 24 78       	mov    %r13,0x78(%rsp)
  3cc139:	48 8b 5c 24 28       	mov    0x28(%rsp),%rbx
  3cc13e:	48 39 cb             	cmp    %rcx,%rbx
  3cc141:	74 14                	je     3cc157 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1d17>
  3cc143:	48 89 5c 24 78       	mov    %rbx,0x78(%rsp)
  3cc148:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3cc14d:	48 89 84 24 88 00 00 	mov    %rax,0x88(%rsp)
  3cc154:	00 
  3cc155:	eb 0d                	jmp    3cc164 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1d24>
  3cc157:	66 0f 10 01          	movupd (%rcx),%xmm0
  3cc15b:	66 41 0f 11 45 00    	movupd %xmm0,0x0(%r13)
  3cc161:	4c 89 eb             	mov    %r13,%rbx
  3cc164:	4c 8b 74 24 30       	mov    0x30(%rsp),%r14
  3cc169:	4c 89 b4 24 80 00 00 	mov    %r14,0x80(%rsp)
  3cc170:	00 
  3cc171:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cc176:	48 c7 44 24 30 00 00 	movq   $0x0,0x30(%rsp)
  3cc17d:	00 00 
  3cc17f:	c6 44 24 38 00       	movb   $0x0,0x38(%rsp)
  3cc184:	48 c7 44 24 68 00 00 	movq   $0x0,0x68(%rsp)
  3cc18b:	00 00 
  3cc18d:	bf 28 00 00 00       	mov    $0x28,%edi
  3cc192:	e8 c9 b0 de ff       	call   1b7260 <_Znwm@plt>
  3cc197:	48 89 c1             	mov    %rax,%rcx
  3cc19a:	48 83 c1 10          	add    $0x10,%rcx
  3cc19e:	48 89 08             	mov    %rcx,(%rax)
  3cc1a1:	4c 39 eb             	cmp    %r13,%rbx
  3cc1a4:	74 11                	je     3cc1b7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1d77>
  3cc1a6:	48 89 18             	mov    %rbx,(%rax)
  3cc1a9:	48 8b 8c 24 88 00 00 	mov    0x88(%rsp),%rcx
  3cc1b0:	00 
  3cc1b1:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3cc1b5:	eb 0a                	jmp    3cc1c1 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1d81>
  3cc1b7:	66 41 0f 10 45 00    	movupd 0x0(%r13),%xmm0
  3cc1bd:	66 0f 11 01          	movupd %xmm0,(%rcx)
  3cc1c1:	4c 89 6c 24 78       	mov    %r13,0x78(%rsp)
  3cc1c6:	48 c7 84 24 80 00 00 	movq   $0x0,0x80(%rsp)
  3cc1cd:	00 00 00 00 00 
  3cc1d2:	c6 84 24 88 00 00 00 	movb   $0x0,0x88(%rsp)
  3cc1d9:	00 
  3cc1da:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3cc1de:	48 89 44 24 58       	mov    %rax,0x58(%rsp)
  3cc1e3:	48 8d 05 e6 a5 01 00 	lea    0x1a5e6(%rip),%rax        # 3e67d0 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_32vEEE9_M_invokeERKSt9_Any_data>
  3cc1ea:	48 89 44 24 70       	mov    %rax,0x70(%rsp)
  3cc1ef:	48 8d 05 ba a7 01 00 	lea    0x1a7ba(%rip),%rax        # 3e69b0 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_32vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3cc1f6:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cc1fb:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3cc202:	00 00 
  3cc204:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3cc209:	48 8d 94 24 a0 00 00 	lea    0xa0(%rsp),%rdx
  3cc210:	00 
  3cc211:	48 8d 4c 24 58       	lea    0x58(%rsp),%rcx
  3cc216:	31 f6                	xor    %esi,%esi
  3cc218:	e8 73 7a de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3cc21d:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3cc222:	48 85 ff             	test   %rdi,%rdi
  3cc225:	74 17                	je     3cc23e <_ZN5MCLoc20DoNormalUpdateActionEv+0x1dfe>
  3cc227:	48 8b 07             	mov    (%rdi),%rax
  3cc22a:	48 8b 35 9f d7 52 00 	mov    0x52d79f(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3cc231:	ff 50 20             	call   *0x20(%rax)
  3cc234:	48 89 c3             	mov    %rax,%rbx
  3cc237:	4c 8b 6c 24 50       	mov    0x50(%rsp),%r13
  3cc23c:	eb 05                	jmp    3cc243 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1e03>
  3cc23e:	45 31 ed             	xor    %r13d,%r13d
  3cc241:	31 db                	xor    %ebx,%ebx
  3cc243:	48 89 5c 24 48       	mov    %rbx,0x48(%rsp)
  3cc248:	4d 85 ed             	test   %r13,%r13
  3cc24b:	74 17                	je     3cc264 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1e24>
  3cc24d:	48 83 3d db d8 52 00 	cmpq   $0x0,0x52d8db(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cc254:	00 
  3cc255:	74 08                	je     3cc25f <_ZN5MCLoc20DoNormalUpdateActionEv+0x1e1f>
  3cc257:	f0 41 83 45 08 01    	lock addl $0x1,0x8(%r13)
  3cc25d:	eb 05                	jmp    3cc264 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1e24>
  3cc25f:	41 83 45 08 01       	addl   $0x1,0x8(%r13)
  3cc264:	48 c7 84 24 b0 00 00 	movq   $0x0,0xb0(%rsp)
  3cc26b:	00 00 00 00 00 
  3cc270:	bf 10 00 00 00       	mov    $0x10,%edi
  3cc275:	e8 e6 af de ff       	call   1b7260 <_Znwm@plt>
  3cc27a:	48 89 18             	mov    %rbx,(%rax)
  3cc27d:	4c 89 68 08          	mov    %r13,0x8(%rax)
  3cc281:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3cc288:	00 
  3cc289:	48 8d 05 50 a8 01 00 	lea    0x1a850(%rip),%rax        # 3e6ae0 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_32JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3cc290:	48 89 84 24 b8 00 00 	mov    %rax,0xb8(%rsp)
  3cc297:	00 
  3cc298:	48 8d 05 71 a8 01 00 	lea    0x1a871(%rip),%rax        # 3e6b10 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_32JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3cc29f:	48 89 84 24 b0 00 00 	mov    %rax,0xb0(%rsp)
  3cc2a6:	00 
  3cc2a7:	49 8d 7c 24 08       	lea    0x8(%r12),%rdi
  3cc2ac:	48 8d b4 24 a0 00 00 	lea    0xa0(%rsp),%rsi
  3cc2b3:	00 
  3cc2b4:	e8 47 5b de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3cc2b9:	49 81 c4 c0 01 00 00 	add    $0x1c0,%r12
  3cc2c0:	4c 89 e7             	mov    %r12,%rdi
  3cc2c3:	e8 a8 be de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3cc2c8:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3cc2cd:	48 8d bc 24 70 03 00 	lea    0x370(%rsp),%rdi
  3cc2d4:	00 
  3cc2d5:	e8 f6 cd de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3cc2da:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3cc2e1:	00 
  3cc2e2:	48 85 c0             	test   %rax,%rax
  3cc2e5:	4c 8b ac 24 f0 02 00 	mov    0x2f0(%rsp),%r13
  3cc2ec:	00 
  3cc2ed:	74 12                	je     3cc301 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1ec1>
  3cc2ef:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3cc2f6:	00 
  3cc2f7:	ba 03 00 00 00       	mov    $0x3,%edx
  3cc2fc:	48 89 fe             	mov    %rdi,%rsi
  3cc2ff:	ff d0                	call   *%rax
  3cc301:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3cc306:	48 85 db             	test   %rbx,%rbx
  3cc309:	4c 8b b4 24 e8 02 00 	mov    0x2e8(%rsp),%r14
  3cc310:	00 
  3cc311:	4c 8b a4 24 e0 02 00 	mov    0x2e0(%rsp),%r12
  3cc318:	00 
  3cc319:	74 64                	je     3cc37f <_ZN5MCLoc20DoNormalUpdateActionEv+0x1f3f>
  3cc31b:	48 83 3d 0d d8 52 00 	cmpq   $0x0,0x52d80d(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cc322:	00 
  3cc323:	74 11                	je     3cc336 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1ef6>
  3cc325:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cc32a:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cc32f:	83 f8 01             	cmp    $0x1,%eax
  3cc332:	74 10                	je     3cc344 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1f04>
  3cc334:	eb 49                	jmp    3cc37f <_ZN5MCLoc20DoNormalUpdateActionEv+0x1f3f>
  3cc336:	8b 43 08             	mov    0x8(%rbx),%eax
  3cc339:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cc33c:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cc33f:	83 f8 01             	cmp    $0x1,%eax
  3cc342:	75 3b                	jne    3cc37f <_ZN5MCLoc20DoNormalUpdateActionEv+0x1f3f>
  3cc344:	48 8b 03             	mov    (%rbx),%rax
  3cc347:	48 89 df             	mov    %rbx,%rdi
  3cc34a:	ff 50 10             	call   *0x10(%rax)
  3cc34d:	48 83 3d db d7 52 00 	cmpq   $0x0,0x52d7db(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cc354:	00 
  3cc355:	74 11                	je     3cc368 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1f28>
  3cc357:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cc35c:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cc361:	83 f8 01             	cmp    $0x1,%eax
  3cc364:	74 10                	je     3cc376 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1f36>
  3cc366:	eb 17                	jmp    3cc37f <_ZN5MCLoc20DoNormalUpdateActionEv+0x1f3f>
  3cc368:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cc36b:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cc36e:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cc371:	83 f8 01             	cmp    $0x1,%eax
  3cc374:	75 09                	jne    3cc37f <_ZN5MCLoc20DoNormalUpdateActionEv+0x1f3f>
  3cc376:	48 8b 03             	mov    (%rbx),%rax
  3cc379:	48 89 df             	mov    %rbx,%rdi
  3cc37c:	ff 50 18             	call   *0x18(%rax)
  3cc37f:	48 8b 44 24 68       	mov    0x68(%rsp),%rax
  3cc384:	48 85 c0             	test   %rax,%rax
  3cc387:	74 0f                	je     3cc398 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1f58>
  3cc389:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3cc38e:	ba 03 00 00 00       	mov    $0x3,%edx
  3cc393:	48 89 fe             	mov    %rdi,%rsi
  3cc396:	ff d0                	call   *%rax
  3cc398:	48 8b 9c 24 78 03 00 	mov    0x378(%rsp),%rbx
  3cc39f:	00 
  3cc3a0:	48 85 db             	test   %rbx,%rbx
  3cc3a3:	74 64                	je     3cc409 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1fc9>
  3cc3a5:	48 83 3d 83 d7 52 00 	cmpq   $0x0,0x52d783(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cc3ac:	00 
  3cc3ad:	74 11                	je     3cc3c0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1f80>
  3cc3af:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cc3b4:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cc3b9:	83 f8 01             	cmp    $0x1,%eax
  3cc3bc:	74 10                	je     3cc3ce <_ZN5MCLoc20DoNormalUpdateActionEv+0x1f8e>
  3cc3be:	eb 49                	jmp    3cc409 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1fc9>
  3cc3c0:	8b 43 08             	mov    0x8(%rbx),%eax
  3cc3c3:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cc3c6:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cc3c9:	83 f8 01             	cmp    $0x1,%eax
  3cc3cc:	75 3b                	jne    3cc409 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1fc9>
  3cc3ce:	48 8b 03             	mov    (%rbx),%rax
  3cc3d1:	48 89 df             	mov    %rbx,%rdi
  3cc3d4:	ff 50 10             	call   *0x10(%rax)
  3cc3d7:	48 83 3d 51 d7 52 00 	cmpq   $0x0,0x52d751(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cc3de:	00 
  3cc3df:	74 11                	je     3cc3f2 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1fb2>
  3cc3e1:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cc3e6:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cc3eb:	83 f8 01             	cmp    $0x1,%eax
  3cc3ee:	74 10                	je     3cc400 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1fc0>
  3cc3f0:	eb 17                	jmp    3cc409 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1fc9>
  3cc3f2:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cc3f5:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cc3f8:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cc3fb:	83 f8 01             	cmp    $0x1,%eax
  3cc3fe:	75 09                	jne    3cc409 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1fc9>
  3cc400:	48 8b 03             	mov    (%rbx),%rax
  3cc403:	48 89 df             	mov    %rbx,%rdi
  3cc406:	ff 50 18             	call   *0x18(%rax)
  3cc409:	48 8b 7c 24 28       	mov    0x28(%rsp),%rdi
  3cc40e:	48 8d 44 24 38       	lea    0x38(%rsp),%rax
  3cc413:	48 39 c7             	cmp    %rax,%rdi
  3cc416:	74 05                	je     3cc41d <_ZN5MCLoc20DoNormalUpdateActionEv+0x1fdd>
  3cc418:	e8 d3 34 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cc41d:	48 8b bc 24 c8 00 00 	mov    0xc8(%rsp),%rdi
  3cc424:	00 
  3cc425:	48 8d 84 24 d8 00 00 	lea    0xd8(%rsp),%rax
  3cc42c:	00 
  3cc42d:	48 39 c7             	cmp    %rax,%rdi
  3cc430:	74 05                	je     3cc437 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1ff7>
  3cc432:	e8 b9 34 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cc437:	48 8b 84 24 00 01 00 	mov    0x100(%rsp),%rax
  3cc43e:	00 
  3cc43f:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cc446:	00 
  3cc447:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cc44b:	48 8b 8c 24 f0 00 00 	mov    0xf0(%rsp),%rcx
  3cc452:	00 
  3cc453:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cc45a:	00 
  3cc45b:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  3cc462:	00 
  3cc463:	48 89 84 24 28 01 00 	mov    %rax,0x128(%rsp)
  3cc46a:	00 
  3cc46b:	48 8b 84 24 10 01 00 	mov    0x110(%rsp),%rax
  3cc472:	00 
  3cc473:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cc47a:	00 
  3cc47b:	48 8b bc 24 78 01 00 	mov    0x178(%rsp),%rdi
  3cc482:	00 
  3cc483:	48 8d 84 24 88 01 00 	lea    0x188(%rsp),%rax
  3cc48a:	00 
  3cc48b:	48 39 c7             	cmp    %rax,%rdi
  3cc48e:	74 05                	je     3cc495 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2055>
  3cc490:	e8 5b 34 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cc495:	4c 89 ac 24 30 01 00 	mov    %r13,0x130(%rsp)
  3cc49c:	00 
  3cc49d:	48 8d bc 24 68 01 00 	lea    0x168(%rsp),%rdi
  3cc4a4:	00 
  3cc4a5:	e8 56 76 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3cc4aa:	4c 89 a4 24 18 01 00 	mov    %r12,0x118(%rsp)
  3cc4b1:	00 
  3cc4b2:	49 8b 44 24 e8       	mov    -0x18(%r12),%rax
  3cc4b7:	4c 89 b4 04 18 01 00 	mov    %r14,0x118(%rsp,%rax,1)
  3cc4be:	00 
  3cc4bf:	48 c7 84 24 20 01 00 	movq   $0x0,0x120(%rsp)
  3cc4c6:	00 00 00 00 00 
  3cc4cb:	48 8d bc 24 98 01 00 	lea    0x198(%rsp),%rdi
  3cc4d2:	00 
  3cc4d3:	e8 e8 c1 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3cc4d8:	49 8b bf a8 d2 d0 03 	mov    0x3d0d2a8(%r15),%rdi
  3cc4df:	49 8b 87 f0 cc d0 03 	mov    0x3d0ccf0(%r15),%rax
  3cc4e6:	66 48 0f 6e c8       	movq   %rax,%xmm1
  3cc4eb:	31 c0                	xor    %eax,%eax
  3cc4ed:	41 86 87 88 cc d0 03 	xchg   %al,0x3d0cc88(%r15)
  3cc4f4:	48 8b 84 24 d8 02 00 	mov    0x2d8(%rsp),%rax
  3cc4fb:	00 
  3cc4fc:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
  3cc501:	0f 10 84 24 c8 02 00 	movups 0x2c8(%rsp),%xmm0
  3cc508:	00 
  3cc509:	0f 11 04 24          	movups %xmm0,(%rsp)
  3cc50d:	f3 0f 7e 05 c3 64 19 	movq   0x1964c3(%rip),%xmm0        # 5629d8 <_ZTS11errorLogger+0x8e>
  3cc514:	00 
  3cc515:	e8 86 9d de ff       	call   1b62a0 <_ZN3rbk9algorithm16MCLMotionModel2D18setExtraMoveParamsEddNS0_10StateVar2DE@plt>
  3cc51a:	48 8d 94 24 a0 02 00 	lea    0x2a0(%rsp),%rdx
  3cc521:	00 
  3cc522:	be 03 00 00 00       	mov    $0x3,%esi
  3cc527:	48 8b bc 24 f8 00 00 	mov    0xf8(%rsp),%rdi
  3cc52e:	00 
  3cc52f:	e8 bc 28 de ff       	call   1aedf0 <_ZN3rbk9algorithm16ParticleFilter2D15ParticlesActionENS1_9Whats2RunERSt6vectorIdSaIdEE@plt>
  3cc534:	4c 89 ff             	mov    %r15,%rdi
  3cc537:	e8 c4 bb de ff       	call   1b8100 <_ZN5MCLoc15UpdateParticlesERN3rbk9algorithm10StateVar2DE@plt>
  3cc53c:	41 c6 87 18 0f 00 00 	movb   $0x1,0xf18(%r15)
  3cc543:	01 
  3cc544:	4c 89 ff             	mov    %r15,%rdi
  3cc547:	e8 44 5c de ff       	call   1b2190 <_ZN5MCLoc24SetLastVartoMeanParticleEv@plt>
  3cc54c:	48 8b bc 24 a0 02 00 	mov    0x2a0(%rsp),%rdi
  3cc553:	00 
  3cc554:	48 85 ff             	test   %rdi,%rdi
  3cc557:	74 05                	je     3cc55e <_ZN5MCLoc20DoNormalUpdateActionEv+0x211e>
  3cc559:	e8 92 33 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cc55e:	48 8d bc 24 f8 02 00 	lea    0x2f8(%rsp),%rdi
  3cc565:	00 
  3cc566:	e8 25 45 de ff       	call   1b0a90 <_ZN8profiler10ScopedZoneD1Ev@plt>
  3cc56b:	48 8d 65 d8          	lea    -0x28(%rbp),%rsp
  3cc56f:	5b                   	pop    %rbx
  3cc570:	41 5c                	pop    %r12
  3cc572:	41 5d                	pop    %r13
  3cc574:	41 5e                	pop    %r14
  3cc576:	41 5f                	pop    %r15
  3cc578:	5d                   	pop    %rbp
  3cc579:	c3                   	ret    
  3cc57a:	49 89 cf             	mov    %rcx,%r15
  3cc57d:	4c 89 f7             	mov    %r14,%rdi
  3cc580:	4c 89 ee             	mov    %r13,%rsi
  3cc583:	48 89 da             	mov    %rbx,%rdx
  3cc586:	e8 f5 a9 de ff       	call   1b6f80 <memcpy@plt>
  3cc58b:	4c 89 f9             	mov    %r15,%rcx
  3cc58e:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3cc595:	00 
  3cc596:	48 89 5c 24 30       	mov    %rbx,0x30(%rsp)
  3cc59b:	41 c6 04 1e 00       	movb   $0x0,(%r14,%rbx,1)
  3cc5a0:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3cc5a5:	48 8b 5c 24 28       	mov    0x28(%rsp),%rbx
  3cc5aa:	48 39 cb             	cmp    %rcx,%rbx
  3cc5ad:	74 14                	je     3cc5c3 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2183>
  3cc5af:	48 89 5c 24 78       	mov    %rbx,0x78(%rsp)
  3cc5b4:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3cc5b9:	48 89 84 24 88 00 00 	mov    %rax,0x88(%rsp)
  3cc5c0:	00 
  3cc5c1:	eb 0c                	jmp    3cc5cf <_ZN5MCLoc20DoNormalUpdateActionEv+0x218f>
  3cc5c3:	f3 0f 6f 01          	movdqu (%rcx),%xmm0
  3cc5c7:	f3 41 0f 7f 07       	movdqu %xmm0,(%r15)
  3cc5cc:	4c 89 fb             	mov    %r15,%rbx
  3cc5cf:	4c 8b 74 24 30       	mov    0x30(%rsp),%r14
  3cc5d4:	4c 89 b4 24 80 00 00 	mov    %r14,0x80(%rsp)
  3cc5db:	00 
  3cc5dc:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cc5e1:	48 c7 44 24 30 00 00 	movq   $0x0,0x30(%rsp)
  3cc5e8:	00 00 
  3cc5ea:	c6 44 24 38 00       	movb   $0x0,0x38(%rsp)
  3cc5ef:	48 c7 44 24 68 00 00 	movq   $0x0,0x68(%rsp)
  3cc5f6:	00 00 
  3cc5f8:	bf 28 00 00 00       	mov    $0x28,%edi
  3cc5fd:	e8 5e ac de ff       	call   1b7260 <_Znwm@plt>
  3cc602:	48 89 c1             	mov    %rax,%rcx
  3cc605:	48 83 c1 10          	add    $0x10,%rcx
  3cc609:	48 89 08             	mov    %rcx,(%rax)
  3cc60c:	4c 39 fb             	cmp    %r15,%rbx
  3cc60f:	74 11                	je     3cc622 <_ZN5MCLoc20DoNormalUpdateActionEv+0x21e2>
  3cc611:	48 89 18             	mov    %rbx,(%rax)
  3cc614:	48 8b 8c 24 88 00 00 	mov    0x88(%rsp),%rcx
  3cc61b:	00 
  3cc61c:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3cc620:	eb 09                	jmp    3cc62b <_ZN5MCLoc20DoNormalUpdateActionEv+0x21eb>
  3cc622:	f3 41 0f 6f 07       	movdqu (%r15),%xmm0
  3cc627:	f3 0f 7f 01          	movdqu %xmm0,(%rcx)
  3cc62b:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3cc630:	48 c7 84 24 80 00 00 	movq   $0x0,0x80(%rsp)
  3cc637:	00 00 00 00 00 
  3cc63c:	c6 84 24 88 00 00 00 	movb   $0x0,0x88(%rsp)
  3cc643:	00 
  3cc644:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3cc648:	48 89 44 24 58       	mov    %rax,0x58(%rsp)
  3cc64d:	48 8d 05 bc 98 01 00 	lea    0x198bc(%rip),%rax        # 3e5f10 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_30vEEE9_M_invokeERKSt9_Any_data>
  3cc654:	48 89 44 24 70       	mov    %rax,0x70(%rsp)
  3cc659:	48 8d 05 90 9a 01 00 	lea    0x19a90(%rip),%rax        # 3e60f0 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_30vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3cc660:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cc665:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3cc66c:	00 00 
  3cc66e:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3cc673:	48 8d 94 24 a0 00 00 	lea    0xa0(%rsp),%rdx
  3cc67a:	00 
  3cc67b:	48 8d 4c 24 58       	lea    0x58(%rsp),%rcx
  3cc680:	31 f6                	xor    %esi,%esi
  3cc682:	e8 09 76 de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3cc687:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3cc68c:	48 85 ff             	test   %rdi,%rdi
  3cc68f:	4c 8b bc 24 c0 00 00 	mov    0xc0(%rsp),%r15
  3cc696:	00 
  3cc697:	74 17                	je     3cc6b0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2270>
  3cc699:	48 8b 07             	mov    (%rdi),%rax
  3cc69c:	48 8b 35 2d d3 52 00 	mov    0x52d32d(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3cc6a3:	ff 50 20             	call   *0x20(%rax)
  3cc6a6:	48 89 c3             	mov    %rax,%rbx
  3cc6a9:	4c 8b 6c 24 50       	mov    0x50(%rsp),%r13
  3cc6ae:	eb 05                	jmp    3cc6b5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2275>
  3cc6b0:	45 31 ed             	xor    %r13d,%r13d
  3cc6b3:	31 db                	xor    %ebx,%ebx
  3cc6b5:	48 89 5c 24 48       	mov    %rbx,0x48(%rsp)
  3cc6ba:	4d 85 ed             	test   %r13,%r13
  3cc6bd:	0f 84 80 01 00 00    	je     3cc843 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2403>
  3cc6c3:	48 83 3d 65 d4 52 00 	cmpq   $0x0,0x52d465(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cc6ca:	00 
  3cc6cb:	0f 84 6d 01 00 00    	je     3cc83e <_ZN5MCLoc20DoNormalUpdateActionEv+0x23fe>
  3cc6d1:	f0 41 83 45 08 01    	lock addl $0x1,0x8(%r13)
  3cc6d7:	e9 67 01 00 00       	jmp    3cc843 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2403>
  3cc6dc:	49 89 cf             	mov    %rcx,%r15
  3cc6df:	4c 89 f7             	mov    %r14,%rdi
  3cc6e2:	4c 89 ee             	mov    %r13,%rsi
  3cc6e5:	48 89 da             	mov    %rbx,%rdx
  3cc6e8:	e8 93 a8 de ff       	call   1b6f80 <memcpy@plt>
  3cc6ed:	4c 89 f9             	mov    %r15,%rcx
  3cc6f0:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3cc6f7:	00 
  3cc6f8:	48 89 5c 24 30       	mov    %rbx,0x30(%rsp)
  3cc6fd:	41 c6 04 1e 00       	movb   $0x0,(%r14,%rbx,1)
  3cc702:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3cc707:	48 8b 5c 24 28       	mov    0x28(%rsp),%rbx
  3cc70c:	48 39 cb             	cmp    %rcx,%rbx
  3cc70f:	74 14                	je     3cc725 <_ZN5MCLoc20DoNormalUpdateActionEv+0x22e5>
  3cc711:	48 89 5c 24 78       	mov    %rbx,0x78(%rsp)
  3cc716:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3cc71b:	48 89 84 24 88 00 00 	mov    %rax,0x88(%rsp)
  3cc722:	00 
  3cc723:	eb 0c                	jmp    3cc731 <_ZN5MCLoc20DoNormalUpdateActionEv+0x22f1>
  3cc725:	f3 0f 6f 01          	movdqu (%rcx),%xmm0
  3cc729:	f3 41 0f 7f 07       	movdqu %xmm0,(%r15)
  3cc72e:	4c 89 fb             	mov    %r15,%rbx
  3cc731:	4c 8b 74 24 30       	mov    0x30(%rsp),%r14
  3cc736:	4c 89 b4 24 80 00 00 	mov    %r14,0x80(%rsp)
  3cc73d:	00 
  3cc73e:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cc743:	48 c7 44 24 30 00 00 	movq   $0x0,0x30(%rsp)
  3cc74a:	00 00 
  3cc74c:	c6 44 24 38 00       	movb   $0x0,0x38(%rsp)
  3cc751:	48 c7 44 24 68 00 00 	movq   $0x0,0x68(%rsp)
  3cc758:	00 00 
  3cc75a:	bf 28 00 00 00       	mov    $0x28,%edi
  3cc75f:	e8 fc aa de ff       	call   1b7260 <_Znwm@plt>
  3cc764:	48 89 c1             	mov    %rax,%rcx
  3cc767:	48 83 c1 10          	add    $0x10,%rcx
  3cc76b:	48 89 08             	mov    %rcx,(%rax)
  3cc76e:	4c 39 fb             	cmp    %r15,%rbx
  3cc771:	74 11                	je     3cc784 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2344>
  3cc773:	48 89 18             	mov    %rbx,(%rax)
  3cc776:	48 8b 8c 24 88 00 00 	mov    0x88(%rsp),%rcx
  3cc77d:	00 
  3cc77e:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3cc782:	eb 09                	jmp    3cc78d <_ZN5MCLoc20DoNormalUpdateActionEv+0x234d>
  3cc784:	f3 41 0f 6f 07       	movdqu (%r15),%xmm0
  3cc789:	f3 0f 7f 01          	movdqu %xmm0,(%rcx)
  3cc78d:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3cc792:	48 c7 84 24 80 00 00 	movq   $0x0,0x80(%rsp)
  3cc799:	00 00 00 00 00 
  3cc79e:	c6 84 24 88 00 00 00 	movb   $0x0,0x88(%rsp)
  3cc7a5:	00 
  3cc7a6:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3cc7aa:	48 89 44 24 58       	mov    %rax,0x58(%rsp)
  3cc7af:	48 8d 05 fa 92 01 00 	lea    0x192fa(%rip),%rax        # 3e5ab0 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_29vEEE9_M_invokeERKSt9_Any_data>
  3cc7b6:	48 89 44 24 70       	mov    %rax,0x70(%rsp)
  3cc7bb:	48 8d 05 ce 94 01 00 	lea    0x194ce(%rip),%rax        # 3e5c90 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_29vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3cc7c2:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cc7c7:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3cc7ce:	00 00 
  3cc7d0:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3cc7d5:	48 8d 94 24 a0 00 00 	lea    0xa0(%rsp),%rdx
  3cc7dc:	00 
  3cc7dd:	48 8d 4c 24 58       	lea    0x58(%rsp),%rcx
  3cc7e2:	31 f6                	xor    %esi,%esi
  3cc7e4:	e8 a7 74 de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3cc7e9:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3cc7ee:	48 85 ff             	test   %rdi,%rdi
  3cc7f1:	4c 8b bc 24 c0 00 00 	mov    0xc0(%rsp),%r15
  3cc7f8:	00 
  3cc7f9:	74 17                	je     3cc812 <_ZN5MCLoc20DoNormalUpdateActionEv+0x23d2>
  3cc7fb:	48 8b 07             	mov    (%rdi),%rax
  3cc7fe:	48 8b 35 cb d1 52 00 	mov    0x52d1cb(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3cc805:	ff 50 20             	call   *0x20(%rax)
  3cc808:	48 89 c3             	mov    %rax,%rbx
  3cc80b:	4c 8b 6c 24 50       	mov    0x50(%rsp),%r13
  3cc810:	eb 05                	jmp    3cc817 <_ZN5MCLoc20DoNormalUpdateActionEv+0x23d7>
  3cc812:	45 31 ed             	xor    %r13d,%r13d
  3cc815:	31 db                	xor    %ebx,%ebx
  3cc817:	48 89 5c 24 48       	mov    %rbx,0x48(%rsp)
  3cc81c:	4d 85 ed             	test   %r13,%r13
  3cc81f:	0f 84 ec 00 00 00    	je     3cc911 <_ZN5MCLoc20DoNormalUpdateActionEv+0x24d1>
  3cc825:	48 83 3d 03 d3 52 00 	cmpq   $0x0,0x52d303(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cc82c:	00 
  3cc82d:	0f 84 d9 00 00 00    	je     3cc90c <_ZN5MCLoc20DoNormalUpdateActionEv+0x24cc>
  3cc833:	f0 41 83 45 08 01    	lock addl $0x1,0x8(%r13)
  3cc839:	e9 d3 00 00 00       	jmp    3cc911 <_ZN5MCLoc20DoNormalUpdateActionEv+0x24d1>
  3cc83e:	41 83 45 08 01       	addl   $0x1,0x8(%r13)
  3cc843:	48 c7 84 24 b0 00 00 	movq   $0x0,0xb0(%rsp)
  3cc84a:	00 00 00 00 00 
  3cc84f:	bf 10 00 00 00       	mov    $0x10,%edi
  3cc854:	e8 07 aa de ff       	call   1b7260 <_Znwm@plt>
  3cc859:	48 89 18             	mov    %rbx,(%rax)
  3cc85c:	4c 89 68 08          	mov    %r13,0x8(%rax)
  3cc860:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3cc867:	00 
  3cc868:	48 8d 05 b1 99 01 00 	lea    0x199b1(%rip),%rax        # 3e6220 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_30JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3cc86f:	48 89 84 24 b8 00 00 	mov    %rax,0xb8(%rsp)
  3cc876:	00 
  3cc877:	48 8d 05 d2 99 01 00 	lea    0x199d2(%rip),%rax        # 3e6250 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_30JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3cc87e:	48 89 84 24 b0 00 00 	mov    %rax,0xb0(%rsp)
  3cc885:	00 
  3cc886:	49 8d 7c 24 08       	lea    0x8(%r12),%rdi
  3cc88b:	48 8d b4 24 a0 00 00 	lea    0xa0(%rsp),%rsi
  3cc892:	00 
  3cc893:	e8 68 55 de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3cc898:	49 81 c4 c0 01 00 00 	add    $0x1c0,%r12
  3cc89f:	4c 89 e7             	mov    %r12,%rdi
  3cc8a2:	e8 c9 b8 de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3cc8a7:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3cc8ac:	48 8d bc 24 90 03 00 	lea    0x390(%rsp),%rdi
  3cc8b3:	00 
  3cc8b4:	e8 17 c8 de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3cc8b9:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3cc8c0:	00 
  3cc8c1:	48 85 c0             	test   %rax,%rax
  3cc8c4:	74 12                	je     3cc8d8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2498>
  3cc8c6:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3cc8cd:	00 
  3cc8ce:	ba 03 00 00 00       	mov    $0x3,%edx
  3cc8d3:	48 89 fe             	mov    %rdi,%rsi
  3cc8d6:	ff d0                	call   *%rax
  3cc8d8:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3cc8dd:	48 85 db             	test   %rbx,%rbx
  3cc8e0:	0f 84 31 01 00 00    	je     3cca17 <_ZN5MCLoc20DoNormalUpdateActionEv+0x25d7>
  3cc8e6:	48 83 3d 42 d2 52 00 	cmpq   $0x0,0x52d242(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cc8ed:	00 
  3cc8ee:	0f 84 e6 00 00 00    	je     3cc9da <_ZN5MCLoc20DoNormalUpdateActionEv+0x259a>
  3cc8f4:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cc8f9:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cc8fe:	83 f8 01             	cmp    $0x1,%eax
  3cc901:	0f 84 e1 00 00 00    	je     3cc9e8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x25a8>
  3cc907:	e9 0b 01 00 00       	jmp    3cca17 <_ZN5MCLoc20DoNormalUpdateActionEv+0x25d7>
  3cc90c:	41 83 45 08 01       	addl   $0x1,0x8(%r13)
  3cc911:	48 c7 84 24 b0 00 00 	movq   $0x0,0xb0(%rsp)
  3cc918:	00 00 00 00 00 
  3cc91d:	bf 10 00 00 00       	mov    $0x10,%edi
  3cc922:	e8 39 a9 de ff       	call   1b7260 <_Znwm@plt>
  3cc927:	48 89 18             	mov    %rbx,(%rax)
  3cc92a:	4c 89 68 08          	mov    %r13,0x8(%rax)
  3cc92e:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3cc935:	00 
  3cc936:	48 8d 05 83 94 01 00 	lea    0x19483(%rip),%rax        # 3e5dc0 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_29JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3cc93d:	48 89 84 24 b8 00 00 	mov    %rax,0xb8(%rsp)
  3cc944:	00 
  3cc945:	48 8d 05 a4 94 01 00 	lea    0x194a4(%rip),%rax        # 3e5df0 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_29JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3cc94c:	48 89 84 24 b0 00 00 	mov    %rax,0xb0(%rsp)
  3cc953:	00 
  3cc954:	49 8d 7c 24 08       	lea    0x8(%r12),%rdi
  3cc959:	48 8d b4 24 a0 00 00 	lea    0xa0(%rsp),%rsi
  3cc960:	00 
  3cc961:	e8 9a 54 de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3cc966:	49 81 c4 c0 01 00 00 	add    $0x1c0,%r12
  3cc96d:	4c 89 e7             	mov    %r12,%rdi
  3cc970:	e8 fb b7 de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3cc975:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3cc97a:	48 8d bc 24 a0 03 00 	lea    0x3a0(%rsp),%rdi
  3cc981:	00 
  3cc982:	e8 49 c7 de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3cc987:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3cc98e:	00 
  3cc98f:	48 85 c0             	test   %rax,%rax
  3cc992:	74 12                	je     3cc9a6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2566>
  3cc994:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3cc99b:	00 
  3cc99c:	ba 03 00 00 00       	mov    $0x3,%edx
  3cc9a1:	48 89 fe             	mov    %rdi,%rsi
  3cc9a4:	ff d0                	call   *%rax
  3cc9a6:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3cc9ab:	48 85 db             	test   %rbx,%rbx
  3cc9ae:	0f 84 f0 00 00 00    	je     3ccaa4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2664>
  3cc9b4:	48 83 3d 74 d1 52 00 	cmpq   $0x0,0x52d174(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cc9bb:	00 
  3cc9bc:	0f 84 a5 00 00 00    	je     3cca67 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2627>
  3cc9c2:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cc9c7:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cc9cc:	83 f8 01             	cmp    $0x1,%eax
  3cc9cf:	0f 84 a0 00 00 00    	je     3cca75 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2635>
  3cc9d5:	e9 ca 00 00 00       	jmp    3ccaa4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2664>
  3cc9da:	8b 43 08             	mov    0x8(%rbx),%eax
  3cc9dd:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cc9e0:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cc9e3:	83 f8 01             	cmp    $0x1,%eax
  3cc9e6:	75 2f                	jne    3cca17 <_ZN5MCLoc20DoNormalUpdateActionEv+0x25d7>
  3cc9e8:	48 8b 03             	mov    (%rbx),%rax
  3cc9eb:	48 89 df             	mov    %rbx,%rdi
  3cc9ee:	ff 50 10             	call   *0x10(%rax)
  3cc9f1:	48 83 3d 37 d1 52 00 	cmpq   $0x0,0x52d137(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cc9f8:	00 
  3cc9f9:	0f 84 a5 10 00 00    	je     3cdaa4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3664>
  3cc9ff:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cca04:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cca09:	83 f8 01             	cmp    $0x1,%eax
  3cca0c:	75 09                	jne    3cca17 <_ZN5MCLoc20DoNormalUpdateActionEv+0x25d7>
  3cca0e:	48 8b 03             	mov    (%rbx),%rax
  3cca11:	48 89 df             	mov    %rbx,%rdi
  3cca14:	ff 50 18             	call   *0x18(%rax)
  3cca17:	48 8b 44 24 68       	mov    0x68(%rsp),%rax
  3cca1c:	48 85 c0             	test   %rax,%rax
  3cca1f:	74 0f                	je     3cca30 <_ZN5MCLoc20DoNormalUpdateActionEv+0x25f0>
  3cca21:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3cca26:	ba 03 00 00 00       	mov    $0x3,%edx
  3cca2b:	48 89 fe             	mov    %rdi,%rsi
  3cca2e:	ff d0                	call   *%rax
  3cca30:	48 8b 9c 24 98 03 00 	mov    0x398(%rsp),%rbx
  3cca37:	00 
  3cca38:	48 85 db             	test   %rbx,%rbx
  3cca3b:	0f 84 f0 00 00 00    	je     3ccb31 <_ZN5MCLoc20DoNormalUpdateActionEv+0x26f1>
  3cca41:	48 83 3d e7 d0 52 00 	cmpq   $0x0,0x52d0e7(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cca48:	00 
  3cca49:	0f 84 a5 00 00 00    	je     3ccaf4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x26b4>
  3cca4f:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cca54:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cca59:	83 f8 01             	cmp    $0x1,%eax
  3cca5c:	0f 84 a0 00 00 00    	je     3ccb02 <_ZN5MCLoc20DoNormalUpdateActionEv+0x26c2>
  3cca62:	e9 ca 00 00 00       	jmp    3ccb31 <_ZN5MCLoc20DoNormalUpdateActionEv+0x26f1>
  3cca67:	8b 43 08             	mov    0x8(%rbx),%eax
  3cca6a:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cca6d:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cca70:	83 f8 01             	cmp    $0x1,%eax
  3cca73:	75 2f                	jne    3ccaa4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2664>
  3cca75:	48 8b 03             	mov    (%rbx),%rax
  3cca78:	48 89 df             	mov    %rbx,%rdi
  3cca7b:	ff 50 10             	call   *0x10(%rax)
  3cca7e:	48 83 3d aa d0 52 00 	cmpq   $0x0,0x52d0aa(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cca85:	00 
  3cca86:	0f 84 2f 10 00 00    	je     3cdabb <_ZN5MCLoc20DoNormalUpdateActionEv+0x367b>
  3cca8c:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cca91:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cca96:	83 f8 01             	cmp    $0x1,%eax
  3cca99:	75 09                	jne    3ccaa4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2664>
  3cca9b:	48 8b 03             	mov    (%rbx),%rax
  3cca9e:	48 89 df             	mov    %rbx,%rdi
  3ccaa1:	ff 50 18             	call   *0x18(%rax)
  3ccaa4:	48 8b 44 24 68       	mov    0x68(%rsp),%rax
  3ccaa9:	48 85 c0             	test   %rax,%rax
  3ccaac:	74 0f                	je     3ccabd <_ZN5MCLoc20DoNormalUpdateActionEv+0x267d>
  3ccaae:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3ccab3:	ba 03 00 00 00       	mov    $0x3,%edx
  3ccab8:	48 89 fe             	mov    %rdi,%rsi
  3ccabb:	ff d0                	call   *%rax
  3ccabd:	48 8b 9c 24 a8 03 00 	mov    0x3a8(%rsp),%rbx
  3ccac4:	00 
  3ccac5:	48 85 db             	test   %rbx,%rbx
  3ccac8:	0f 84 91 01 00 00    	je     3ccc5f <_ZN5MCLoc20DoNormalUpdateActionEv+0x281f>
  3ccace:	48 83 3d 5a d0 52 00 	cmpq   $0x0,0x52d05a(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ccad5:	00 
  3ccad6:	0f 84 46 01 00 00    	je     3ccc22 <_ZN5MCLoc20DoNormalUpdateActionEv+0x27e2>
  3ccadc:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ccae1:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3ccae6:	83 f8 01             	cmp    $0x1,%eax
  3ccae9:	0f 84 41 01 00 00    	je     3ccc30 <_ZN5MCLoc20DoNormalUpdateActionEv+0x27f0>
  3ccaef:	e9 6b 01 00 00       	jmp    3ccc5f <_ZN5MCLoc20DoNormalUpdateActionEv+0x281f>
  3ccaf4:	8b 43 08             	mov    0x8(%rbx),%eax
  3ccaf7:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ccafa:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3ccafd:	83 f8 01             	cmp    $0x1,%eax
  3ccb00:	75 2f                	jne    3ccb31 <_ZN5MCLoc20DoNormalUpdateActionEv+0x26f1>
  3ccb02:	48 8b 03             	mov    (%rbx),%rax
  3ccb05:	48 89 df             	mov    %rbx,%rdi
  3ccb08:	ff 50 10             	call   *0x10(%rax)
  3ccb0b:	48 83 3d 1d d0 52 00 	cmpq   $0x0,0x52d01d(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ccb12:	00 
  3ccb13:	0f 84 b9 0f 00 00    	je     3cdad2 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3692>
  3ccb19:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ccb1e:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3ccb23:	83 f8 01             	cmp    $0x1,%eax
  3ccb26:	75 09                	jne    3ccb31 <_ZN5MCLoc20DoNormalUpdateActionEv+0x26f1>
  3ccb28:	48 8b 03             	mov    (%rbx),%rax
  3ccb2b:	48 89 df             	mov    %rbx,%rdi
  3ccb2e:	ff 50 18             	call   *0x18(%rax)
  3ccb31:	48 8b 7c 24 28       	mov    0x28(%rsp),%rdi
  3ccb36:	48 8d 44 24 38       	lea    0x38(%rsp),%rax
  3ccb3b:	48 39 c7             	cmp    %rax,%rdi
  3ccb3e:	74 05                	je     3ccb45 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2705>
  3ccb40:	e8 ab 2d de ff       	call   1af8f0 <_ZdlPv@plt>
  3ccb45:	48 8b bc 24 c8 00 00 	mov    0xc8(%rsp),%rdi
  3ccb4c:	00 
  3ccb4d:	48 8d 84 24 d8 00 00 	lea    0xd8(%rsp),%rax
  3ccb54:	00 
  3ccb55:	48 39 c7             	cmp    %rax,%rdi
  3ccb58:	74 05                	je     3ccb5f <_ZN5MCLoc20DoNormalUpdateActionEv+0x271f>
  3ccb5a:	e8 91 2d de ff       	call   1af8f0 <_ZdlPv@plt>
  3ccb5f:	48 8b 1d 62 df 52 00 	mov    0x52df62(%rip),%rbx        # 8faac8 <_ZTTNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3ccb66:	48 8b 03             	mov    (%rbx),%rax
  3ccb69:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3ccb70:	00 
  3ccb71:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  3ccb75:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3ccb79:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3ccb80:	00 
  3ccb81:	48 8b 43 48          	mov    0x48(%rbx),%rax
  3ccb85:	48 89 84 24 28 01 00 	mov    %rax,0x128(%rsp)
  3ccb8c:	00 
  3ccb8d:	48 8b 05 5c a7 52 00 	mov    0x52a75c(%rip),%rax        # 8f72f0 <_ZTVNSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3ccb94:	48 83 c0 10          	add    $0x10,%rax
  3ccb98:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3ccb9f:	00 
  3ccba0:	48 8b bc 24 78 01 00 	mov    0x178(%rsp),%rdi
  3ccba7:	00 
  3ccba8:	48 8d 84 24 88 01 00 	lea    0x188(%rsp),%rax
  3ccbaf:	00 
  3ccbb0:	48 39 c7             	cmp    %rax,%rdi
  3ccbb3:	74 05                	je     3ccbba <_ZN5MCLoc20DoNormalUpdateActionEv+0x277a>
  3ccbb5:	e8 36 2d de ff       	call   1af8f0 <_ZdlPv@plt>
  3ccbba:	48 8b 05 8f be 52 00 	mov    0x52be8f(%rip),%rax        # 8f8a50 <_ZTVSt15basic_streambufIcSt11char_traitsIcEE@GLIBCXX_3.4>
  3ccbc1:	48 83 c0 10          	add    $0x10,%rax
  3ccbc5:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3ccbcc:	00 
  3ccbcd:	48 8d bc 24 68 01 00 	lea    0x168(%rsp),%rdi
  3ccbd4:	00 
  3ccbd5:	e8 26 6f de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3ccbda:	48 8b 43 10          	mov    0x10(%rbx),%rax
  3ccbde:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  3ccbe2:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3ccbe9:	00 
  3ccbea:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3ccbee:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3ccbf5:	00 
  3ccbf6:	48 c7 84 24 20 01 00 	movq   $0x0,0x120(%rsp)
  3ccbfd:	00 00 00 00 00 
  3ccc02:	48 8d bc 24 98 01 00 	lea    0x198(%rsp),%rdi
  3ccc09:	00 
  3ccc0a:	e8 b1 ba de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3ccc0f:	41 80 bf f9 19 00 00 	cmpb   $0x0,0x19f9(%r15)
  3ccc16:	00 
  3ccc17:	0f 85 0f ef ff ff    	jne    3cbb2c <_ZN5MCLoc20DoNormalUpdateActionEv+0x16ec>
  3ccc1d:	e9 12 f9 ff ff       	jmp    3cc534 <_ZN5MCLoc20DoNormalUpdateActionEv+0x20f4>
  3ccc22:	8b 43 08             	mov    0x8(%rbx),%eax
  3ccc25:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ccc28:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3ccc2b:	83 f8 01             	cmp    $0x1,%eax
  3ccc2e:	75 2f                	jne    3ccc5f <_ZN5MCLoc20DoNormalUpdateActionEv+0x281f>
  3ccc30:	48 8b 03             	mov    (%rbx),%rax
  3ccc33:	48 89 df             	mov    %rbx,%rdi
  3ccc36:	ff 50 10             	call   *0x10(%rax)
  3ccc39:	48 83 3d ef ce 52 00 	cmpq   $0x0,0x52ceef(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ccc40:	00 
  3ccc41:	0f 84 a2 0e 00 00    	je     3cdae9 <_ZN5MCLoc20DoNormalUpdateActionEv+0x36a9>
  3ccc47:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ccc4c:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3ccc51:	83 f8 01             	cmp    $0x1,%eax
  3ccc54:	75 09                	jne    3ccc5f <_ZN5MCLoc20DoNormalUpdateActionEv+0x281f>
  3ccc56:	48 8b 03             	mov    (%rbx),%rax
  3ccc59:	48 89 df             	mov    %rbx,%rdi
  3ccc5c:	ff 50 18             	call   *0x18(%rax)
  3ccc5f:	48 8b 7c 24 28       	mov    0x28(%rsp),%rdi
  3ccc64:	48 8d 44 24 38       	lea    0x38(%rsp),%rax
  3ccc69:	48 39 c7             	cmp    %rax,%rdi
  3ccc6c:	74 05                	je     3ccc73 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2833>
  3ccc6e:	e8 7d 2c de ff       	call   1af8f0 <_ZdlPv@plt>
  3ccc73:	48 8b bc 24 c8 00 00 	mov    0xc8(%rsp),%rdi
  3ccc7a:	00 
  3ccc7b:	48 8d 84 24 d8 00 00 	lea    0xd8(%rsp),%rax
  3ccc82:	00 
  3ccc83:	48 39 c7             	cmp    %rax,%rdi
  3ccc86:	74 05                	je     3ccc8d <_ZN5MCLoc20DoNormalUpdateActionEv+0x284d>
  3ccc88:	e8 63 2c de ff       	call   1af8f0 <_ZdlPv@plt>
  3ccc8d:	48 8b 1d 34 de 52 00 	mov    0x52de34(%rip),%rbx        # 8faac8 <_ZTTNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3ccc94:	48 8b 03             	mov    (%rbx),%rax
  3ccc97:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3ccc9e:	00 
  3ccc9f:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  3ccca3:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3ccca7:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cccae:	00 
  3cccaf:	48 8b 43 48          	mov    0x48(%rbx),%rax
  3cccb3:	48 89 84 24 28 01 00 	mov    %rax,0x128(%rsp)
  3cccba:	00 
  3cccbb:	48 8b 05 2e a6 52 00 	mov    0x52a62e(%rip),%rax        # 8f72f0 <_ZTVNSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cccc2:	48 83 c0 10          	add    $0x10,%rax
  3cccc6:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3ccccd:	00 
  3cccce:	48 8b bc 24 78 01 00 	mov    0x178(%rsp),%rdi
  3cccd5:	00 
  3cccd6:	48 8d 84 24 88 01 00 	lea    0x188(%rsp),%rax
  3cccdd:	00 
  3cccde:	48 39 c7             	cmp    %rax,%rdi
  3ccce1:	74 05                	je     3ccce8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x28a8>
  3ccce3:	e8 08 2c de ff       	call   1af8f0 <_ZdlPv@plt>
  3ccce8:	48 8b 05 61 bd 52 00 	mov    0x52bd61(%rip),%rax        # 8f8a50 <_ZTVSt15basic_streambufIcSt11char_traitsIcEE@GLIBCXX_3.4>
  3cccef:	48 83 c0 10          	add    $0x10,%rax
  3cccf3:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cccfa:	00 
  3cccfb:	48 8d bc 24 68 01 00 	lea    0x168(%rsp),%rdi
  3ccd02:	00 
  3ccd03:	e8 f8 6d de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3ccd08:	48 8b 43 10          	mov    0x10(%rbx),%rax
  3ccd0c:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  3ccd10:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3ccd17:	00 
  3ccd18:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3ccd1c:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3ccd23:	00 
  3ccd24:	48 c7 84 24 20 01 00 	movq   $0x0,0x120(%rsp)
  3ccd2b:	00 00 00 00 00 
  3ccd30:	48 8d bc 24 98 01 00 	lea    0x198(%rsp),%rdi
  3ccd37:	00 
  3ccd38:	e8 83 b9 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3ccd3d:	49 8b bf a8 d2 d0 03 	mov    0x3d0d2a8(%r15),%rdi
  3ccd44:	49 8b 87 20 cc d0 03 	mov    0x3d0cc20(%r15),%rax
  3ccd4b:	66 48 0f 6e c0       	movq   %rax,%xmm0
  3ccd50:	31 c0                	xor    %eax,%eax
  3ccd52:	31 c9                	xor    %ecx,%ecx
  3ccd54:	41 86 8f b8 cb d0 03 	xchg   %cl,0x3d0cbb8(%r15)
  3ccd5b:	49 8b 8f f0 cc d0 03 	mov    0x3d0ccf0(%r15),%rcx
  3ccd62:	66 48 0f 6e c9       	movq   %rcx,%xmm1
  3ccd67:	41 86 87 88 cc d0 03 	xchg   %al,0x3d0cc88(%r15)
  3ccd6e:	48 8b 84 24 d8 02 00 	mov    0x2d8(%rsp),%rax
  3ccd75:	00 
  3ccd76:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
  3ccd7b:	66 0f 10 94 24 c8 02 	movupd 0x2c8(%rsp),%xmm2
  3ccd82:	00 00 
  3ccd84:	66 0f 11 14 24       	movupd %xmm2,(%rsp)
  3ccd89:	e8 12 95 de ff       	call   1b62a0 <_ZN3rbk9algorithm16MCLMotionModel2D18setExtraMoveParamsEddNS0_10StateVar2DE@plt>
  3ccd8e:	48 8d 94 24 a0 02 00 	lea    0x2a0(%rsp),%rdx
  3ccd95:	00 
  3ccd96:	be 03 00 00 00       	mov    $0x3,%esi
  3ccd9b:	48 8b bc 24 f8 00 00 	mov    0xf8(%rsp),%rdi
  3ccda2:	00 
  3ccda3:	e8 48 20 de ff       	call   1aedf0 <_ZN3rbk9algorithm16ParticleFilter2D15ParticlesActionENS1_9Whats2RunERSt6vectorIdSaIdEE@plt>
  3ccda8:	e9 71 ed ff ff       	jmp    3cbb1e <_ZN5MCLoc20DoNormalUpdateActionEv+0x16de>
  3ccdad:	49 89 cf             	mov    %rcx,%r15
  3ccdb0:	4c 89 f7             	mov    %r14,%rdi
  3ccdb3:	4c 89 ee             	mov    %r13,%rsi
  3ccdb6:	48 89 da             	mov    %rbx,%rdx
  3ccdb9:	e8 c2 a1 de ff       	call   1b6f80 <memcpy@plt>
  3ccdbe:	4c 89 f9             	mov    %r15,%rcx
  3ccdc1:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3ccdc8:	00 
  3ccdc9:	48 89 5c 24 30       	mov    %rbx,0x30(%rsp)
  3ccdce:	41 c6 04 1e 00       	movb   $0x0,(%r14,%rbx,1)
  3ccdd3:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3ccdd8:	48 8b 5c 24 28       	mov    0x28(%rsp),%rbx
  3ccddd:	48 39 cb             	cmp    %rcx,%rbx
  3ccde0:	74 14                	je     3ccdf6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x29b6>
  3ccde2:	48 89 5c 24 78       	mov    %rbx,0x78(%rsp)
  3ccde7:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3ccdec:	48 89 84 24 88 00 00 	mov    %rax,0x88(%rsp)
  3ccdf3:	00 
  3ccdf4:	eb 0c                	jmp    3cce02 <_ZN5MCLoc20DoNormalUpdateActionEv+0x29c2>
  3ccdf6:	f3 0f 6f 01          	movdqu (%rcx),%xmm0
  3ccdfa:	f3 41 0f 7f 07       	movdqu %xmm0,(%r15)
  3ccdff:	4c 89 fb             	mov    %r15,%rbx
  3cce02:	4c 8b 74 24 30       	mov    0x30(%rsp),%r14
  3cce07:	4c 89 b4 24 80 00 00 	mov    %r14,0x80(%rsp)
  3cce0e:	00 
  3cce0f:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cce14:	48 c7 44 24 30 00 00 	movq   $0x0,0x30(%rsp)
  3cce1b:	00 00 
  3cce1d:	c6 44 24 38 00       	movb   $0x0,0x38(%rsp)
  3cce22:	48 c7 44 24 68 00 00 	movq   $0x0,0x68(%rsp)
  3cce29:	00 00 
  3cce2b:	bf 28 00 00 00       	mov    $0x28,%edi
  3cce30:	e8 2b a4 de ff       	call   1b7260 <_Znwm@plt>
  3cce35:	48 89 c1             	mov    %rax,%rcx
  3cce38:	48 83 c1 10          	add    $0x10,%rcx
  3cce3c:	48 89 08             	mov    %rcx,(%rax)
  3cce3f:	4c 39 fb             	cmp    %r15,%rbx
  3cce42:	74 11                	je     3cce55 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2a15>
  3cce44:	48 89 18             	mov    %rbx,(%rax)
  3cce47:	48 8b 8c 24 88 00 00 	mov    0x88(%rsp),%rcx
  3cce4e:	00 
  3cce4f:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3cce53:	eb 09                	jmp    3cce5e <_ZN5MCLoc20DoNormalUpdateActionEv+0x2a1e>
  3cce55:	f3 41 0f 6f 07       	movdqu (%r15),%xmm0
  3cce5a:	f3 0f 7f 01          	movdqu %xmm0,(%rcx)
  3cce5e:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3cce63:	48 c7 84 24 80 00 00 	movq   $0x0,0x80(%rsp)
  3cce6a:	00 00 00 00 00 
  3cce6f:	c6 84 24 88 00 00 00 	movb   $0x0,0x88(%rsp)
  3cce76:	00 
  3cce77:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3cce7b:	48 89 44 24 58       	mov    %rax,0x58(%rsp)
  3cce80:	48 8d 05 a9 7a 01 00 	lea    0x17aa9(%rip),%rax        # 3e4930 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_25vEEE9_M_invokeERKSt9_Any_data>
  3cce87:	48 89 44 24 70       	mov    %rax,0x70(%rsp)
  3cce8c:	48 8d 05 7d 7c 01 00 	lea    0x17c7d(%rip),%rax        # 3e4b10 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_25vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3cce93:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cce98:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3cce9f:	00 00 
  3ccea1:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3ccea6:	48 8d 94 24 a0 00 00 	lea    0xa0(%rsp),%rdx
  3ccead:	00 
  3cceae:	48 8d 4c 24 58       	lea    0x58(%rsp),%rcx
  3cceb3:	31 f6                	xor    %esi,%esi
  3cceb5:	e8 d6 6d de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3cceba:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3ccebf:	48 85 ff             	test   %rdi,%rdi
  3ccec2:	4c 8b bc 24 c0 00 00 	mov    0xc0(%rsp),%r15
  3ccec9:	00 
  3cceca:	74 17                	je     3ccee3 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2aa3>
  3ccecc:	48 8b 07             	mov    (%rdi),%rax
  3ccecf:	48 8b 35 fa ca 52 00 	mov    0x52cafa(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3cced6:	ff 50 20             	call   *0x20(%rax)
  3cced9:	48 89 c3             	mov    %rax,%rbx
  3ccedc:	4c 8b 6c 24 50       	mov    0x50(%rsp),%r13
  3ccee1:	eb 05                	jmp    3ccee8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2aa8>
  3ccee3:	45 31 ed             	xor    %r13d,%r13d
  3ccee6:	31 db                	xor    %ebx,%ebx
  3ccee8:	48 89 5c 24 48       	mov    %rbx,0x48(%rsp)
  3cceed:	4d 85 ed             	test   %r13,%r13
  3ccef0:	0f 84 e2 02 00 00    	je     3cd1d8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2d98>
  3ccef6:	48 83 3d 32 cc 52 00 	cmpq   $0x0,0x52cc32(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ccefd:	00 
  3ccefe:	0f 84 cf 02 00 00    	je     3cd1d3 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2d93>
  3ccf04:	f0 41 83 45 08 01    	lock addl $0x1,0x8(%r13)
  3ccf0a:	e9 c9 02 00 00       	jmp    3cd1d8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2d98>
  3ccf0f:	49 89 cf             	mov    %rcx,%r15
  3ccf12:	4c 89 f7             	mov    %r14,%rdi
  3ccf15:	4c 89 ee             	mov    %r13,%rsi
  3ccf18:	48 89 da             	mov    %rbx,%rdx
  3ccf1b:	e8 60 a0 de ff       	call   1b6f80 <memcpy@plt>
  3ccf20:	4c 89 f9             	mov    %r15,%rcx
  3ccf23:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3ccf2a:	00 
  3ccf2b:	48 89 5c 24 30       	mov    %rbx,0x30(%rsp)
  3ccf30:	41 c6 04 1e 00       	movb   $0x0,(%r14,%rbx,1)
  3ccf35:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3ccf3a:	48 8b 5c 24 28       	mov    0x28(%rsp),%rbx
  3ccf3f:	48 39 cb             	cmp    %rcx,%rbx
  3ccf42:	74 14                	je     3ccf58 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2b18>
  3ccf44:	48 89 5c 24 78       	mov    %rbx,0x78(%rsp)
  3ccf49:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3ccf4e:	48 89 84 24 88 00 00 	mov    %rax,0x88(%rsp)
  3ccf55:	00 
  3ccf56:	eb 0c                	jmp    3ccf64 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2b24>
  3ccf58:	f3 0f 6f 01          	movdqu (%rcx),%xmm0
  3ccf5c:	f3 41 0f 7f 07       	movdqu %xmm0,(%r15)
  3ccf61:	4c 89 fb             	mov    %r15,%rbx
  3ccf64:	4c 8b 74 24 30       	mov    0x30(%rsp),%r14
  3ccf69:	4c 89 b4 24 80 00 00 	mov    %r14,0x80(%rsp)
  3ccf70:	00 
  3ccf71:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3ccf76:	48 c7 44 24 30 00 00 	movq   $0x0,0x30(%rsp)
  3ccf7d:	00 00 
  3ccf7f:	c6 44 24 38 00       	movb   $0x0,0x38(%rsp)
  3ccf84:	48 c7 44 24 68 00 00 	movq   $0x0,0x68(%rsp)
  3ccf8b:	00 00 
  3ccf8d:	bf 28 00 00 00       	mov    $0x28,%edi
  3ccf92:	e8 c9 a2 de ff       	call   1b7260 <_Znwm@plt>
  3ccf97:	48 89 c1             	mov    %rax,%rcx
  3ccf9a:	48 83 c1 10          	add    $0x10,%rcx
  3ccf9e:	48 89 08             	mov    %rcx,(%rax)
  3ccfa1:	4c 39 fb             	cmp    %r15,%rbx
  3ccfa4:	74 11                	je     3ccfb7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2b77>
  3ccfa6:	48 89 18             	mov    %rbx,(%rax)
  3ccfa9:	48 8b 8c 24 88 00 00 	mov    0x88(%rsp),%rcx
  3ccfb0:	00 
  3ccfb1:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3ccfb5:	eb 09                	jmp    3ccfc0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2b80>
  3ccfb7:	f3 41 0f 6f 07       	movdqu (%r15),%xmm0
  3ccfbc:	f3 0f 7f 01          	movdqu %xmm0,(%rcx)
  3ccfc0:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3ccfc5:	48 c7 84 24 80 00 00 	movq   $0x0,0x80(%rsp)
  3ccfcc:	00 00 00 00 00 
  3ccfd1:	c6 84 24 88 00 00 00 	movb   $0x0,0x88(%rsp)
  3ccfd8:	00 
  3ccfd9:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3ccfdd:	48 89 44 24 58       	mov    %rax,0x58(%rsp)
  3ccfe2:	48 8d 05 07 82 01 00 	lea    0x18207(%rip),%rax        # 3e51f0 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_27vEEE9_M_invokeERKSt9_Any_data>
  3ccfe9:	48 89 44 24 70       	mov    %rax,0x70(%rsp)
  3ccfee:	48 8d 05 db 83 01 00 	lea    0x183db(%rip),%rax        # 3e53d0 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_27vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3ccff5:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3ccffa:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3cd001:	00 00 
  3cd003:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3cd008:	48 8d 94 24 a0 00 00 	lea    0xa0(%rsp),%rdx
  3cd00f:	00 
  3cd010:	48 8d 4c 24 58       	lea    0x58(%rsp),%rcx
  3cd015:	31 f6                	xor    %esi,%esi
  3cd017:	e8 74 6c de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3cd01c:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3cd021:	48 85 ff             	test   %rdi,%rdi
  3cd024:	4c 8b bc 24 c0 00 00 	mov    0xc0(%rsp),%r15
  3cd02b:	00 
  3cd02c:	74 17                	je     3cd045 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2c05>
  3cd02e:	48 8b 07             	mov    (%rdi),%rax
  3cd031:	48 8b 35 98 c9 52 00 	mov    0x52c998(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3cd038:	ff 50 20             	call   *0x20(%rax)
  3cd03b:	48 89 c3             	mov    %rax,%rbx
  3cd03e:	4c 8b 6c 24 50       	mov    0x50(%rsp),%r13
  3cd043:	eb 05                	jmp    3cd04a <_ZN5MCLoc20DoNormalUpdateActionEv+0x2c0a>
  3cd045:	45 31 ed             	xor    %r13d,%r13d
  3cd048:	31 db                	xor    %ebx,%ebx
  3cd04a:	48 89 5c 24 48       	mov    %rbx,0x48(%rsp)
  3cd04f:	4d 85 ed             	test   %r13,%r13
  3cd052:	0f 84 4e 02 00 00    	je     3cd2a6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2e66>
  3cd058:	48 83 3d d0 ca 52 00 	cmpq   $0x0,0x52cad0(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd05f:	00 
  3cd060:	0f 84 3b 02 00 00    	je     3cd2a1 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2e61>
  3cd066:	f0 41 83 45 08 01    	lock addl $0x1,0x8(%r13)
  3cd06c:	e9 35 02 00 00       	jmp    3cd2a6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2e66>
  3cd071:	49 89 cf             	mov    %rcx,%r15
  3cd074:	4c 89 f7             	mov    %r14,%rdi
  3cd077:	4c 89 ee             	mov    %r13,%rsi
  3cd07a:	48 89 da             	mov    %rbx,%rdx
  3cd07d:	e8 fe 9e de ff       	call   1b6f80 <memcpy@plt>
  3cd082:	4c 89 f9             	mov    %r15,%rcx
  3cd085:	4c 8d bc 24 88 00 00 	lea    0x88(%rsp),%r15
  3cd08c:	00 
  3cd08d:	48 89 5c 24 30       	mov    %rbx,0x30(%rsp)
  3cd092:	41 c6 04 1e 00       	movb   $0x0,(%r14,%rbx,1)
  3cd097:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3cd09c:	48 8b 5c 24 28       	mov    0x28(%rsp),%rbx
  3cd0a1:	48 39 cb             	cmp    %rcx,%rbx
  3cd0a4:	74 14                	je     3cd0ba <_ZN5MCLoc20DoNormalUpdateActionEv+0x2c7a>
  3cd0a6:	48 89 5c 24 78       	mov    %rbx,0x78(%rsp)
  3cd0ab:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3cd0b0:	48 89 84 24 88 00 00 	mov    %rax,0x88(%rsp)
  3cd0b7:	00 
  3cd0b8:	eb 0c                	jmp    3cd0c6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2c86>
  3cd0ba:	f3 0f 6f 01          	movdqu (%rcx),%xmm0
  3cd0be:	f3 41 0f 7f 07       	movdqu %xmm0,(%r15)
  3cd0c3:	4c 89 fb             	mov    %r15,%rbx
  3cd0c6:	4c 8b 74 24 30       	mov    0x30(%rsp),%r14
  3cd0cb:	4c 89 b4 24 80 00 00 	mov    %r14,0x80(%rsp)
  3cd0d2:	00 
  3cd0d3:	48 89 4c 24 28       	mov    %rcx,0x28(%rsp)
  3cd0d8:	48 c7 44 24 30 00 00 	movq   $0x0,0x30(%rsp)
  3cd0df:	00 00 
  3cd0e1:	c6 44 24 38 00       	movb   $0x0,0x38(%rsp)
  3cd0e6:	48 c7 44 24 68 00 00 	movq   $0x0,0x68(%rsp)
  3cd0ed:	00 00 
  3cd0ef:	bf 28 00 00 00       	mov    $0x28,%edi
  3cd0f4:	e8 67 a1 de ff       	call   1b7260 <_Znwm@plt>
  3cd0f9:	48 89 c1             	mov    %rax,%rcx
  3cd0fc:	48 83 c1 10          	add    $0x10,%rcx
  3cd100:	48 89 08             	mov    %rcx,(%rax)
  3cd103:	4c 39 fb             	cmp    %r15,%rbx
  3cd106:	74 11                	je     3cd119 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2cd9>
  3cd108:	48 89 18             	mov    %rbx,(%rax)
  3cd10b:	48 8b 8c 24 88 00 00 	mov    0x88(%rsp),%rcx
  3cd112:	00 
  3cd113:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3cd117:	eb 09                	jmp    3cd122 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2ce2>
  3cd119:	f3 41 0f 6f 07       	movdqu (%r15),%xmm0
  3cd11e:	f3 0f 7f 01          	movdqu %xmm0,(%rcx)
  3cd122:	4c 89 7c 24 78       	mov    %r15,0x78(%rsp)
  3cd127:	48 c7 84 24 80 00 00 	movq   $0x0,0x80(%rsp)
  3cd12e:	00 00 00 00 00 
  3cd133:	c6 84 24 88 00 00 00 	movb   $0x0,0x88(%rsp)
  3cd13a:	00 
  3cd13b:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3cd13f:	48 89 44 24 58       	mov    %rax,0x58(%rsp)
  3cd144:	48 8d 05 45 7c 01 00 	lea    0x17c45(%rip),%rax        # 3e4d90 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_26vEEE9_M_invokeERKSt9_Any_data>
  3cd14b:	48 89 44 24 70       	mov    %rax,0x70(%rsp)
  3cd150:	48 8d 05 19 7e 01 00 	lea    0x17e19(%rip),%rax        # 3e4f70 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc20DoNormalUpdateActionEvE4$_26vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3cd157:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cd15c:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3cd163:	00 00 
  3cd165:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3cd16a:	48 8d 94 24 a0 00 00 	lea    0xa0(%rsp),%rdx
  3cd171:	00 
  3cd172:	48 8d 4c 24 58       	lea    0x58(%rsp),%rcx
  3cd177:	31 f6                	xor    %esi,%esi
  3cd179:	e8 12 6b de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3cd17e:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3cd183:	48 85 ff             	test   %rdi,%rdi
  3cd186:	4c 8b bc 24 c0 00 00 	mov    0xc0(%rsp),%r15
  3cd18d:	00 
  3cd18e:	74 17                	je     3cd1a7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2d67>
  3cd190:	48 8b 07             	mov    (%rdi),%rax
  3cd193:	48 8b 35 36 c8 52 00 	mov    0x52c836(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3cd19a:	ff 50 20             	call   *0x20(%rax)
  3cd19d:	48 89 c3             	mov    %rax,%rbx
  3cd1a0:	4c 8b 6c 24 50       	mov    0x50(%rsp),%r13
  3cd1a5:	eb 05                	jmp    3cd1ac <_ZN5MCLoc20DoNormalUpdateActionEv+0x2d6c>
  3cd1a7:	45 31 ed             	xor    %r13d,%r13d
  3cd1aa:	31 db                	xor    %ebx,%ebx
  3cd1ac:	48 89 5c 24 48       	mov    %rbx,0x48(%rsp)
  3cd1b1:	4d 85 ed             	test   %r13,%r13
  3cd1b4:	0f 84 ba 01 00 00    	je     3cd374 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2f34>
  3cd1ba:	48 83 3d 6e c9 52 00 	cmpq   $0x0,0x52c96e(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd1c1:	00 
  3cd1c2:	0f 84 a7 01 00 00    	je     3cd36f <_ZN5MCLoc20DoNormalUpdateActionEv+0x2f2f>
  3cd1c8:	f0 41 83 45 08 01    	lock addl $0x1,0x8(%r13)
  3cd1ce:	e9 a1 01 00 00       	jmp    3cd374 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2f34>
  3cd1d3:	41 83 45 08 01       	addl   $0x1,0x8(%r13)
  3cd1d8:	48 c7 84 24 b0 00 00 	movq   $0x0,0xb0(%rsp)
  3cd1df:	00 00 00 00 00 
  3cd1e4:	bf 10 00 00 00       	mov    $0x10,%edi
  3cd1e9:	e8 72 a0 de ff       	call   1b7260 <_Znwm@plt>
  3cd1ee:	48 89 18             	mov    %rbx,(%rax)
  3cd1f1:	4c 89 68 08          	mov    %r13,0x8(%rax)
  3cd1f5:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3cd1fc:	00 
  3cd1fd:	48 8d 05 3c 7a 01 00 	lea    0x17a3c(%rip),%rax        # 3e4c40 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_25JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3cd204:	48 89 84 24 b8 00 00 	mov    %rax,0xb8(%rsp)
  3cd20b:	00 
  3cd20c:	48 8d 05 5d 7a 01 00 	lea    0x17a5d(%rip),%rax        # 3e4c70 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_25JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3cd213:	48 89 84 24 b0 00 00 	mov    %rax,0xb0(%rsp)
  3cd21a:	00 
  3cd21b:	49 8d 7c 24 08       	lea    0x8(%r12),%rdi
  3cd220:	48 8d b4 24 a0 00 00 	lea    0xa0(%rsp),%rsi
  3cd227:	00 
  3cd228:	e8 d3 4b de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3cd22d:	49 81 c4 c0 01 00 00 	add    $0x1c0,%r12
  3cd234:	4c 89 e7             	mov    %r12,%rdi
  3cd237:	e8 34 af de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3cd23c:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3cd241:	48 8d bc 24 e0 03 00 	lea    0x3e0(%rsp),%rdi
  3cd248:	00 
  3cd249:	e8 82 be de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3cd24e:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3cd255:	00 
  3cd256:	48 85 c0             	test   %rax,%rax
  3cd259:	74 12                	je     3cd26d <_ZN5MCLoc20DoNormalUpdateActionEv+0x2e2d>
  3cd25b:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3cd262:	00 
  3cd263:	ba 03 00 00 00       	mov    $0x3,%edx
  3cd268:	48 89 fe             	mov    %rdi,%rsi
  3cd26b:	ff d0                	call   *%rax
  3cd26d:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3cd272:	48 85 db             	test   %rbx,%rbx
  3cd275:	0f 84 16 02 00 00    	je     3cd491 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3051>
  3cd27b:	48 83 3d ad c8 52 00 	cmpq   $0x0,0x52c8ad(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd282:	00 
  3cd283:	0f 84 cb 01 00 00    	je     3cd454 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3014>
  3cd289:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cd28e:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cd293:	83 f8 01             	cmp    $0x1,%eax
  3cd296:	0f 84 c6 01 00 00    	je     3cd462 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3022>
  3cd29c:	e9 f0 01 00 00       	jmp    3cd491 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3051>
  3cd2a1:	41 83 45 08 01       	addl   $0x1,0x8(%r13)
  3cd2a6:	48 c7 84 24 b0 00 00 	movq   $0x0,0xb0(%rsp)
  3cd2ad:	00 00 00 00 00 
  3cd2b2:	bf 10 00 00 00       	mov    $0x10,%edi
  3cd2b7:	e8 a4 9f de ff       	call   1b7260 <_Znwm@plt>
  3cd2bc:	48 89 18             	mov    %rbx,(%rax)
  3cd2bf:	4c 89 68 08          	mov    %r13,0x8(%rax)
  3cd2c3:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3cd2ca:	00 
  3cd2cb:	48 8d 05 2e 82 01 00 	lea    0x1822e(%rip),%rax        # 3e5500 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_27JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3cd2d2:	48 89 84 24 b8 00 00 	mov    %rax,0xb8(%rsp)
  3cd2d9:	00 
  3cd2da:	48 8d 05 4f 82 01 00 	lea    0x1824f(%rip),%rax        # 3e5530 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_27JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3cd2e1:	48 89 84 24 b0 00 00 	mov    %rax,0xb0(%rsp)
  3cd2e8:	00 
  3cd2e9:	49 8d 7c 24 08       	lea    0x8(%r12),%rdi
  3cd2ee:	48 8d b4 24 a0 00 00 	lea    0xa0(%rsp),%rsi
  3cd2f5:	00 
  3cd2f6:	e8 05 4b de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3cd2fb:	49 81 c4 c0 01 00 00 	add    $0x1c0,%r12
  3cd302:	4c 89 e7             	mov    %r12,%rdi
  3cd305:	e8 66 ae de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3cd30a:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3cd30f:	48 8d bc 24 c0 03 00 	lea    0x3c0(%rsp),%rdi
  3cd316:	00 
  3cd317:	e8 b4 bd de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3cd31c:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3cd323:	00 
  3cd324:	48 85 c0             	test   %rax,%rax
  3cd327:	74 12                	je     3cd33b <_ZN5MCLoc20DoNormalUpdateActionEv+0x2efb>
  3cd329:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3cd330:	00 
  3cd331:	ba 03 00 00 00       	mov    $0x3,%edx
  3cd336:	48 89 fe             	mov    %rdi,%rsi
  3cd339:	ff d0                	call   *%rax
  3cd33b:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3cd340:	48 85 db             	test   %rbx,%rbx
  3cd343:	0f 84 d5 01 00 00    	je     3cd51e <_ZN5MCLoc20DoNormalUpdateActionEv+0x30de>
  3cd349:	48 83 3d df c7 52 00 	cmpq   $0x0,0x52c7df(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd350:	00 
  3cd351:	0f 84 8a 01 00 00    	je     3cd4e1 <_ZN5MCLoc20DoNormalUpdateActionEv+0x30a1>
  3cd357:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cd35c:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cd361:	83 f8 01             	cmp    $0x1,%eax
  3cd364:	0f 84 85 01 00 00    	je     3cd4ef <_ZN5MCLoc20DoNormalUpdateActionEv+0x30af>
  3cd36a:	e9 af 01 00 00       	jmp    3cd51e <_ZN5MCLoc20DoNormalUpdateActionEv+0x30de>
  3cd36f:	41 83 45 08 01       	addl   $0x1,0x8(%r13)
  3cd374:	48 c7 84 24 b0 00 00 	movq   $0x0,0xb0(%rsp)
  3cd37b:	00 00 00 00 00 
  3cd380:	bf 10 00 00 00       	mov    $0x10,%edi
  3cd385:	e8 d6 9e de ff       	call   1b7260 <_Znwm@plt>
  3cd38a:	48 89 18             	mov    %rbx,(%rax)
  3cd38d:	4c 89 68 08          	mov    %r13,0x8(%rax)
  3cd391:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3cd398:	00 
  3cd399:	48 8d 05 00 7d 01 00 	lea    0x17d00(%rip),%rax        # 3e50a0 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_26JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3cd3a0:	48 89 84 24 b8 00 00 	mov    %rax,0xb8(%rsp)
  3cd3a7:	00 
  3cd3a8:	48 8d 05 21 7d 01 00 	lea    0x17d21(%rip),%rax        # 3e50d0 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc20DoNormalUpdateActionEvE4$_26JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3cd3af:	48 89 84 24 b0 00 00 	mov    %rax,0xb0(%rsp)
  3cd3b6:	00 
  3cd3b7:	49 8d 7c 24 08       	lea    0x8(%r12),%rdi
  3cd3bc:	48 8d b4 24 a0 00 00 	lea    0xa0(%rsp),%rsi
  3cd3c3:	00 
  3cd3c4:	e8 37 4a de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3cd3c9:	49 81 c4 c0 01 00 00 	add    $0x1c0,%r12
  3cd3d0:	4c 89 e7             	mov    %r12,%rdi
  3cd3d3:	e8 98 ad de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3cd3d8:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3cd3dd:	48 8d bc 24 d0 03 00 	lea    0x3d0(%rsp),%rdi
  3cd3e4:	00 
  3cd3e5:	e8 e6 bc de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3cd3ea:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3cd3f1:	00 
  3cd3f2:	48 85 c0             	test   %rax,%rax
  3cd3f5:	74 12                	je     3cd409 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2fc9>
  3cd3f7:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3cd3fe:	00 
  3cd3ff:	ba 03 00 00 00       	mov    $0x3,%edx
  3cd404:	48 89 fe             	mov    %rdi,%rsi
  3cd407:	ff d0                	call   *%rax
  3cd409:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3cd40e:	48 85 db             	test   %rbx,%rbx
  3cd411:	0f 84 94 01 00 00    	je     3cd5ab <_ZN5MCLoc20DoNormalUpdateActionEv+0x316b>
  3cd417:	48 83 3d 11 c7 52 00 	cmpq   $0x0,0x52c711(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd41e:	00 
  3cd41f:	0f 84 49 01 00 00    	je     3cd56e <_ZN5MCLoc20DoNormalUpdateActionEv+0x312e>
  3cd425:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cd42a:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cd42f:	83 f8 01             	cmp    $0x1,%eax
  3cd432:	0f 84 44 01 00 00    	je     3cd57c <_ZN5MCLoc20DoNormalUpdateActionEv+0x313c>
  3cd438:	e9 6e 01 00 00       	jmp    3cd5ab <_ZN5MCLoc20DoNormalUpdateActionEv+0x316b>
  3cd43d:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cd440:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cd443:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cd446:	83 f8 01             	cmp    $0x1,%eax
  3cd449:	0f 85 08 e5 ff ff    	jne    3cb957 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1517>
  3cd44f:	e9 fa e4 ff ff       	jmp    3cb94e <_ZN5MCLoc20DoNormalUpdateActionEv+0x150e>
  3cd454:	8b 43 08             	mov    0x8(%rbx),%eax
  3cd457:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cd45a:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cd45d:	83 f8 01             	cmp    $0x1,%eax
  3cd460:	75 2f                	jne    3cd491 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3051>
  3cd462:	48 8b 03             	mov    (%rbx),%rax
  3cd465:	48 89 df             	mov    %rbx,%rdi
  3cd468:	ff 50 10             	call   *0x10(%rax)
  3cd46b:	48 83 3d bd c6 52 00 	cmpq   $0x0,0x52c6bd(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd472:	00 
  3cd473:	0f 84 87 06 00 00    	je     3cdb00 <_ZN5MCLoc20DoNormalUpdateActionEv+0x36c0>
  3cd479:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cd47e:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cd483:	83 f8 01             	cmp    $0x1,%eax
  3cd486:	75 09                	jne    3cd491 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3051>
  3cd488:	48 8b 03             	mov    (%rbx),%rax
  3cd48b:	48 89 df             	mov    %rbx,%rdi
  3cd48e:	ff 50 18             	call   *0x18(%rax)
  3cd491:	48 8b 44 24 68       	mov    0x68(%rsp),%rax
  3cd496:	48 85 c0             	test   %rax,%rax
  3cd499:	74 0f                	je     3cd4aa <_ZN5MCLoc20DoNormalUpdateActionEv+0x306a>
  3cd49b:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3cd4a0:	ba 03 00 00 00       	mov    $0x3,%edx
  3cd4a5:	48 89 fe             	mov    %rdi,%rsi
  3cd4a8:	ff d0                	call   *%rax
  3cd4aa:	48 8b 9c 24 e8 03 00 	mov    0x3e8(%rsp),%rbx
  3cd4b1:	00 
  3cd4b2:	48 85 db             	test   %rbx,%rbx
  3cd4b5:	0f 84 94 01 00 00    	je     3cd64f <_ZN5MCLoc20DoNormalUpdateActionEv+0x320f>
  3cd4bb:	48 83 3d 6d c6 52 00 	cmpq   $0x0,0x52c66d(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd4c2:	00 
  3cd4c3:	0f 84 49 01 00 00    	je     3cd612 <_ZN5MCLoc20DoNormalUpdateActionEv+0x31d2>
  3cd4c9:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cd4ce:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cd4d3:	83 f8 01             	cmp    $0x1,%eax
  3cd4d6:	0f 84 44 01 00 00    	je     3cd620 <_ZN5MCLoc20DoNormalUpdateActionEv+0x31e0>
  3cd4dc:	e9 6e 01 00 00       	jmp    3cd64f <_ZN5MCLoc20DoNormalUpdateActionEv+0x320f>
  3cd4e1:	8b 43 08             	mov    0x8(%rbx),%eax
  3cd4e4:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cd4e7:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cd4ea:	83 f8 01             	cmp    $0x1,%eax
  3cd4ed:	75 2f                	jne    3cd51e <_ZN5MCLoc20DoNormalUpdateActionEv+0x30de>
  3cd4ef:	48 8b 03             	mov    (%rbx),%rax
  3cd4f2:	48 89 df             	mov    %rbx,%rdi
  3cd4f5:	ff 50 10             	call   *0x10(%rax)
  3cd4f8:	48 83 3d 30 c6 52 00 	cmpq   $0x0,0x52c630(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd4ff:	00 
  3cd500:	0f 84 11 06 00 00    	je     3cdb17 <_ZN5MCLoc20DoNormalUpdateActionEv+0x36d7>
  3cd506:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cd50b:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cd510:	83 f8 01             	cmp    $0x1,%eax
  3cd513:	75 09                	jne    3cd51e <_ZN5MCLoc20DoNormalUpdateActionEv+0x30de>
  3cd515:	48 8b 03             	mov    (%rbx),%rax
  3cd518:	48 89 df             	mov    %rbx,%rdi
  3cd51b:	ff 50 18             	call   *0x18(%rax)
  3cd51e:	48 8b 44 24 68       	mov    0x68(%rsp),%rax
  3cd523:	48 85 c0             	test   %rax,%rax
  3cd526:	74 0f                	je     3cd537 <_ZN5MCLoc20DoNormalUpdateActionEv+0x30f7>
  3cd528:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3cd52d:	ba 03 00 00 00       	mov    $0x3,%edx
  3cd532:	48 89 fe             	mov    %rdi,%rsi
  3cd535:	ff d0                	call   *%rax
  3cd537:	48 8b 9c 24 c8 03 00 	mov    0x3c8(%rsp),%rbx
  3cd53e:	00 
  3cd53f:	48 85 db             	test   %rbx,%rbx
  3cd542:	0f 84 92 02 00 00    	je     3cd7da <_ZN5MCLoc20DoNormalUpdateActionEv+0x339a>
  3cd548:	48 83 3d e0 c5 52 00 	cmpq   $0x0,0x52c5e0(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd54f:	00 
  3cd550:	0f 84 47 02 00 00    	je     3cd79d <_ZN5MCLoc20DoNormalUpdateActionEv+0x335d>
  3cd556:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cd55b:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cd560:	83 f8 01             	cmp    $0x1,%eax
  3cd563:	0f 84 42 02 00 00    	je     3cd7ab <_ZN5MCLoc20DoNormalUpdateActionEv+0x336b>
  3cd569:	e9 6c 02 00 00       	jmp    3cd7da <_ZN5MCLoc20DoNormalUpdateActionEv+0x339a>
  3cd56e:	8b 43 08             	mov    0x8(%rbx),%eax
  3cd571:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cd574:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cd577:	83 f8 01             	cmp    $0x1,%eax
  3cd57a:	75 2f                	jne    3cd5ab <_ZN5MCLoc20DoNormalUpdateActionEv+0x316b>
  3cd57c:	48 8b 03             	mov    (%rbx),%rax
  3cd57f:	48 89 df             	mov    %rbx,%rdi
  3cd582:	ff 50 10             	call   *0x10(%rax)
  3cd585:	48 83 3d a3 c5 52 00 	cmpq   $0x0,0x52c5a3(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd58c:	00 
  3cd58d:	0f 84 9b 05 00 00    	je     3cdb2e <_ZN5MCLoc20DoNormalUpdateActionEv+0x36ee>
  3cd593:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cd598:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cd59d:	83 f8 01             	cmp    $0x1,%eax
  3cd5a0:	75 09                	jne    3cd5ab <_ZN5MCLoc20DoNormalUpdateActionEv+0x316b>
  3cd5a2:	48 8b 03             	mov    (%rbx),%rax
  3cd5a5:	48 89 df             	mov    %rbx,%rdi
  3cd5a8:	ff 50 18             	call   *0x18(%rax)
  3cd5ab:	48 8b 44 24 68       	mov    0x68(%rsp),%rax
  3cd5b0:	48 85 c0             	test   %rax,%rax
  3cd5b3:	74 0f                	je     3cd5c4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3184>
  3cd5b5:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3cd5ba:	ba 03 00 00 00       	mov    $0x3,%edx
  3cd5bf:	48 89 fe             	mov    %rdi,%rsi
  3cd5c2:	ff d0                	call   *%rax
  3cd5c4:	48 8b 9c 24 d8 03 00 	mov    0x3d8(%rsp),%rbx
  3cd5cb:	00 
  3cd5cc:	48 85 db             	test   %rbx,%rbx
  3cd5cf:	0f 84 90 03 00 00    	je     3cd965 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3525>
  3cd5d5:	48 83 3d 53 c5 52 00 	cmpq   $0x0,0x52c553(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd5dc:	00 
  3cd5dd:	0f 84 45 03 00 00    	je     3cd928 <_ZN5MCLoc20DoNormalUpdateActionEv+0x34e8>
  3cd5e3:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cd5e8:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cd5ed:	83 f8 01             	cmp    $0x1,%eax
  3cd5f0:	0f 84 40 03 00 00    	je     3cd936 <_ZN5MCLoc20DoNormalUpdateActionEv+0x34f6>
  3cd5f6:	e9 6a 03 00 00       	jmp    3cd965 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3525>
  3cd5fb:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cd5fe:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cd601:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cd604:	83 f8 01             	cmp    $0x1,%eax
  3cd607:	0f 85 c8 e3 ff ff    	jne    3cb9d5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x1595>
  3cd60d:	e9 ba e3 ff ff       	jmp    3cb9cc <_ZN5MCLoc20DoNormalUpdateActionEv+0x158c>
  3cd612:	8b 43 08             	mov    0x8(%rbx),%eax
  3cd615:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cd618:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cd61b:	83 f8 01             	cmp    $0x1,%eax
  3cd61e:	75 2f                	jne    3cd64f <_ZN5MCLoc20DoNormalUpdateActionEv+0x320f>
  3cd620:	48 8b 03             	mov    (%rbx),%rax
  3cd623:	48 89 df             	mov    %rbx,%rdi
  3cd626:	ff 50 10             	call   *0x10(%rax)
  3cd629:	48 83 3d ff c4 52 00 	cmpq   $0x0,0x52c4ff(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd630:	00 
  3cd631:	0f 84 0e 05 00 00    	je     3cdb45 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3705>
  3cd637:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cd63c:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cd641:	83 f8 01             	cmp    $0x1,%eax
  3cd644:	75 09                	jne    3cd64f <_ZN5MCLoc20DoNormalUpdateActionEv+0x320f>
  3cd646:	48 8b 03             	mov    (%rbx),%rax
  3cd649:	48 89 df             	mov    %rbx,%rdi
  3cd64c:	ff 50 18             	call   *0x18(%rax)
  3cd64f:	48 8b 7c 24 28       	mov    0x28(%rsp),%rdi
  3cd654:	48 8d 44 24 38       	lea    0x38(%rsp),%rax
  3cd659:	48 39 c7             	cmp    %rax,%rdi
  3cd65c:	74 05                	je     3cd663 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3223>
  3cd65e:	e8 8d 22 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cd663:	48 8b bc 24 c8 00 00 	mov    0xc8(%rsp),%rdi
  3cd66a:	00 
  3cd66b:	48 8d 84 24 d8 00 00 	lea    0xd8(%rsp),%rax
  3cd672:	00 
  3cd673:	48 39 c7             	cmp    %rax,%rdi
  3cd676:	74 05                	je     3cd67d <_ZN5MCLoc20DoNormalUpdateActionEv+0x323d>
  3cd678:	e8 73 22 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cd67d:	48 8b 1d 44 d4 52 00 	mov    0x52d444(%rip),%rbx        # 8faac8 <_ZTTNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cd684:	48 8b 03             	mov    (%rbx),%rax
  3cd687:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cd68e:	00 
  3cd68f:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  3cd693:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cd697:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cd69e:	00 
  3cd69f:	48 8b 43 48          	mov    0x48(%rbx),%rax
  3cd6a3:	48 89 84 24 28 01 00 	mov    %rax,0x128(%rsp)
  3cd6aa:	00 
  3cd6ab:	48 8b 05 3e 9c 52 00 	mov    0x529c3e(%rip),%rax        # 8f72f0 <_ZTVNSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cd6b2:	48 83 c0 10          	add    $0x10,%rax
  3cd6b6:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cd6bd:	00 
  3cd6be:	48 8b bc 24 78 01 00 	mov    0x178(%rsp),%rdi
  3cd6c5:	00 
  3cd6c6:	48 8d 84 24 88 01 00 	lea    0x188(%rsp),%rax
  3cd6cd:	00 
  3cd6ce:	48 39 c7             	cmp    %rax,%rdi
  3cd6d1:	74 05                	je     3cd6d8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3298>
  3cd6d3:	e8 18 22 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cd6d8:	48 8b 05 71 b3 52 00 	mov    0x52b371(%rip),%rax        # 8f8a50 <_ZTVSt15basic_streambufIcSt11char_traitsIcEE@GLIBCXX_3.4>
  3cd6df:	48 83 c0 10          	add    $0x10,%rax
  3cd6e3:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cd6ea:	00 
  3cd6eb:	48 8d bc 24 68 01 00 	lea    0x168(%rsp),%rdi
  3cd6f2:	00 
  3cd6f3:	e8 08 64 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3cd6f8:	48 8b 43 10          	mov    0x10(%rbx),%rax
  3cd6fc:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  3cd700:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cd707:	00 
  3cd708:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cd70c:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cd713:	00 
  3cd714:	48 c7 84 24 20 01 00 	movq   $0x0,0x120(%rsp)
  3cd71b:	00 00 00 00 00 
  3cd720:	48 8d bc 24 98 01 00 	lea    0x198(%rsp),%rdi
  3cd727:	00 
  3cd728:	e8 93 af de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3cd72d:	49 8b bf a8 d2 d0 03 	mov    0x3d0d2a8(%r15),%rdi
  3cd734:	49 8b 87 e8 c5 d0 03 	mov    0x3d0c5e8(%r15),%rax
  3cd73b:	66 48 0f 6e c0       	movq   %rax,%xmm0
  3cd740:	31 c0                	xor    %eax,%eax
  3cd742:	31 c9                	xor    %ecx,%ecx
  3cd744:	41 86 8f 80 c5 d0 03 	xchg   %cl,0x3d0c580(%r15)
  3cd74b:	49 8b 8f b8 c6 d0 03 	mov    0x3d0c6b8(%r15),%rcx
  3cd752:	66 48 0f 6e c9       	movq   %rcx,%xmm1
  3cd757:	41 86 87 50 c6 d0 03 	xchg   %al,0x3d0c650(%r15)
  3cd75e:	48 8b 84 24 d8 02 00 	mov    0x2d8(%rsp),%rax
  3cd765:	00 
  3cd766:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
  3cd76b:	66 0f 10 94 24 c8 02 	movupd 0x2c8(%rsp),%xmm2
  3cd772:	00 00 
  3cd774:	66 0f 11 14 24       	movupd %xmm2,(%rsp)
  3cd779:	e8 22 8b de ff       	call   1b62a0 <_ZN3rbk9algorithm16MCLMotionModel2D18setExtraMoveParamsEddNS0_10StateVar2DE@plt>
  3cd77e:	48 8d 94 24 a0 02 00 	lea    0x2a0(%rsp),%rdx
  3cd785:	00 
  3cd786:	be 03 00 00 00       	mov    $0x3,%esi
  3cd78b:	48 8b bc 24 f8 00 00 	mov    0xf8(%rsp),%rdi
  3cd792:	00 
  3cd793:	e8 58 16 de ff       	call   1aedf0 <_ZN3rbk9algorithm16ParticleFilter2D15ParticlesActionENS1_9Whats2RunERSt6vectorIdSaIdEE@plt>
  3cd798:	e9 81 e3 ff ff       	jmp    3cbb1e <_ZN5MCLoc20DoNormalUpdateActionEv+0x16de>
  3cd79d:	8b 43 08             	mov    0x8(%rbx),%eax
  3cd7a0:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cd7a3:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cd7a6:	83 f8 01             	cmp    $0x1,%eax
  3cd7a9:	75 2f                	jne    3cd7da <_ZN5MCLoc20DoNormalUpdateActionEv+0x339a>
  3cd7ab:	48 8b 03             	mov    (%rbx),%rax
  3cd7ae:	48 89 df             	mov    %rbx,%rdi
  3cd7b1:	ff 50 10             	call   *0x10(%rax)
  3cd7b4:	48 83 3d 74 c3 52 00 	cmpq   $0x0,0x52c374(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd7bb:	00 
  3cd7bc:	0f 84 9a 03 00 00    	je     3cdb5c <_ZN5MCLoc20DoNormalUpdateActionEv+0x371c>
  3cd7c2:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cd7c7:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cd7cc:	83 f8 01             	cmp    $0x1,%eax
  3cd7cf:	75 09                	jne    3cd7da <_ZN5MCLoc20DoNormalUpdateActionEv+0x339a>
  3cd7d1:	48 8b 03             	mov    (%rbx),%rax
  3cd7d4:	48 89 df             	mov    %rbx,%rdi
  3cd7d7:	ff 50 18             	call   *0x18(%rax)
  3cd7da:	48 8b 7c 24 28       	mov    0x28(%rsp),%rdi
  3cd7df:	48 8d 44 24 38       	lea    0x38(%rsp),%rax
  3cd7e4:	48 39 c7             	cmp    %rax,%rdi
  3cd7e7:	74 05                	je     3cd7ee <_ZN5MCLoc20DoNormalUpdateActionEv+0x33ae>
  3cd7e9:	e8 02 21 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cd7ee:	48 8b bc 24 c8 00 00 	mov    0xc8(%rsp),%rdi
  3cd7f5:	00 
  3cd7f6:	48 8d 84 24 d8 00 00 	lea    0xd8(%rsp),%rax
  3cd7fd:	00 
  3cd7fe:	48 39 c7             	cmp    %rax,%rdi
  3cd801:	74 05                	je     3cd808 <_ZN5MCLoc20DoNormalUpdateActionEv+0x33c8>
  3cd803:	e8 e8 20 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cd808:	48 8b 1d b9 d2 52 00 	mov    0x52d2b9(%rip),%rbx        # 8faac8 <_ZTTNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cd80f:	48 8b 03             	mov    (%rbx),%rax
  3cd812:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cd819:	00 
  3cd81a:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  3cd81e:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cd822:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cd829:	00 
  3cd82a:	48 8b 43 48          	mov    0x48(%rbx),%rax
  3cd82e:	48 89 84 24 28 01 00 	mov    %rax,0x128(%rsp)
  3cd835:	00 
  3cd836:	48 8b 05 b3 9a 52 00 	mov    0x529ab3(%rip),%rax        # 8f72f0 <_ZTVNSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cd83d:	48 83 c0 10          	add    $0x10,%rax
  3cd841:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cd848:	00 
  3cd849:	48 8b bc 24 78 01 00 	mov    0x178(%rsp),%rdi
  3cd850:	00 
  3cd851:	48 8d 84 24 88 01 00 	lea    0x188(%rsp),%rax
  3cd858:	00 
  3cd859:	48 39 c7             	cmp    %rax,%rdi
  3cd85c:	74 05                	je     3cd863 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3423>
  3cd85e:	e8 8d 20 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cd863:	48 8b 05 e6 b1 52 00 	mov    0x52b1e6(%rip),%rax        # 8f8a50 <_ZTVSt15basic_streambufIcSt11char_traitsIcEE@GLIBCXX_3.4>
  3cd86a:	48 83 c0 10          	add    $0x10,%rax
  3cd86e:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cd875:	00 
  3cd876:	48 8d bc 24 68 01 00 	lea    0x168(%rsp),%rdi
  3cd87d:	00 
  3cd87e:	e8 7d 62 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3cd883:	48 8b 43 10          	mov    0x10(%rbx),%rax
  3cd887:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  3cd88b:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cd892:	00 
  3cd893:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cd897:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cd89e:	00 
  3cd89f:	48 c7 84 24 20 01 00 	movq   $0x0,0x120(%rsp)
  3cd8a6:	00 00 00 00 00 
  3cd8ab:	48 8d bc 24 98 01 00 	lea    0x198(%rsp),%rdi
  3cd8b2:	00 
  3cd8b3:	e8 08 ae de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3cd8b8:	49 8b bf a8 d2 d0 03 	mov    0x3d0d2a8(%r15),%rdi
  3cd8bf:	49 8b 87 18 c5 d0 03 	mov    0x3d0c518(%r15),%rax
  3cd8c6:	66 48 0f 6e c0       	movq   %rax,%xmm0
  3cd8cb:	31 c0                	xor    %eax,%eax
  3cd8cd:	31 c9                	xor    %ecx,%ecx
  3cd8cf:	41 86 8f b0 c4 d0 03 	xchg   %cl,0x3d0c4b0(%r15)
  3cd8d6:	49 8b 8f b8 c6 d0 03 	mov    0x3d0c6b8(%r15),%rcx
  3cd8dd:	66 48 0f 6e c9       	movq   %rcx,%xmm1
  3cd8e2:	41 86 87 50 c6 d0 03 	xchg   %al,0x3d0c650(%r15)
  3cd8e9:	48 8b 84 24 d8 02 00 	mov    0x2d8(%rsp),%rax
  3cd8f0:	00 
  3cd8f1:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
  3cd8f6:	66 0f 10 94 24 c8 02 	movupd 0x2c8(%rsp),%xmm2
  3cd8fd:	00 00 
  3cd8ff:	66 0f 11 14 24       	movupd %xmm2,(%rsp)
  3cd904:	e8 97 89 de ff       	call   1b62a0 <_ZN3rbk9algorithm16MCLMotionModel2D18setExtraMoveParamsEddNS0_10StateVar2DE@plt>
  3cd909:	48 8d 94 24 a0 02 00 	lea    0x2a0(%rsp),%rdx
  3cd910:	00 
  3cd911:	be 03 00 00 00       	mov    $0x3,%esi
  3cd916:	48 8b bc 24 f8 00 00 	mov    0xf8(%rsp),%rdi
  3cd91d:	00 
  3cd91e:	e8 cd 14 de ff       	call   1aedf0 <_ZN3rbk9algorithm16ParticleFilter2D15ParticlesActionENS1_9Whats2RunERSt6vectorIdSaIdEE@plt>
  3cd923:	e9 f6 e1 ff ff       	jmp    3cbb1e <_ZN5MCLoc20DoNormalUpdateActionEv+0x16de>
  3cd928:	8b 43 08             	mov    0x8(%rbx),%eax
  3cd92b:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cd92e:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cd931:	83 f8 01             	cmp    $0x1,%eax
  3cd934:	75 2f                	jne    3cd965 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3525>
  3cd936:	48 8b 03             	mov    (%rbx),%rax
  3cd939:	48 89 df             	mov    %rbx,%rdi
  3cd93c:	ff 50 10             	call   *0x10(%rax)
  3cd93f:	48 83 3d e9 c1 52 00 	cmpq   $0x0,0x52c1e9(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cd946:	00 
  3cd947:	0f 84 26 02 00 00    	je     3cdb73 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3733>
  3cd94d:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cd952:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cd957:	83 f8 01             	cmp    $0x1,%eax
  3cd95a:	75 09                	jne    3cd965 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3525>
  3cd95c:	48 8b 03             	mov    (%rbx),%rax
  3cd95f:	48 89 df             	mov    %rbx,%rdi
  3cd962:	ff 50 18             	call   *0x18(%rax)
  3cd965:	48 8b 7c 24 28       	mov    0x28(%rsp),%rdi
  3cd96a:	48 8d 44 24 38       	lea    0x38(%rsp),%rax
  3cd96f:	48 39 c7             	cmp    %rax,%rdi
  3cd972:	74 05                	je     3cd979 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3539>
  3cd974:	e8 77 1f de ff       	call   1af8f0 <_ZdlPv@plt>
  3cd979:	48 8b bc 24 c8 00 00 	mov    0xc8(%rsp),%rdi
  3cd980:	00 
  3cd981:	48 8d 84 24 d8 00 00 	lea    0xd8(%rsp),%rax
  3cd988:	00 
  3cd989:	48 39 c7             	cmp    %rax,%rdi
  3cd98c:	74 05                	je     3cd993 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3553>
  3cd98e:	e8 5d 1f de ff       	call   1af8f0 <_ZdlPv@plt>
  3cd993:	48 8b 1d 2e d1 52 00 	mov    0x52d12e(%rip),%rbx        # 8faac8 <_ZTTNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cd99a:	48 8b 03             	mov    (%rbx),%rax
  3cd99d:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cd9a4:	00 
  3cd9a5:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  3cd9a9:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cd9ad:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cd9b4:	00 
  3cd9b5:	48 8b 43 48          	mov    0x48(%rbx),%rax
  3cd9b9:	48 89 84 24 28 01 00 	mov    %rax,0x128(%rsp)
  3cd9c0:	00 
  3cd9c1:	48 8b 05 28 99 52 00 	mov    0x529928(%rip),%rax        # 8f72f0 <_ZTVNSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cd9c8:	48 83 c0 10          	add    $0x10,%rax
  3cd9cc:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cd9d3:	00 
  3cd9d4:	48 8b bc 24 78 01 00 	mov    0x178(%rsp),%rdi
  3cd9db:	00 
  3cd9dc:	48 8d 84 24 88 01 00 	lea    0x188(%rsp),%rax
  3cd9e3:	00 
  3cd9e4:	48 39 c7             	cmp    %rax,%rdi
  3cd9e7:	74 05                	je     3cd9ee <_ZN5MCLoc20DoNormalUpdateActionEv+0x35ae>
  3cd9e9:	e8 02 1f de ff       	call   1af8f0 <_ZdlPv@plt>
  3cd9ee:	48 8b 05 5b b0 52 00 	mov    0x52b05b(%rip),%rax        # 8f8a50 <_ZTVSt15basic_streambufIcSt11char_traitsIcEE@GLIBCXX_3.4>
  3cd9f5:	48 83 c0 10          	add    $0x10,%rax
  3cd9f9:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cda00:	00 
  3cda01:	48 8d bc 24 68 01 00 	lea    0x168(%rsp),%rdi
  3cda08:	00 
  3cda09:	e8 f2 60 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3cda0e:	48 8b 43 10          	mov    0x10(%rbx),%rax
  3cda12:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  3cda16:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cda1d:	00 
  3cda1e:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cda22:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cda29:	00 
  3cda2a:	48 c7 84 24 20 01 00 	movq   $0x0,0x120(%rsp)
  3cda31:	00 00 00 00 00 
  3cda36:	48 8d bc 24 98 01 00 	lea    0x198(%rsp),%rdi
  3cda3d:	00 
  3cda3e:	e8 7d ac de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3cda43:	49 8b bf a8 d2 d0 03 	mov    0x3d0d2a8(%r15),%rdi
  3cda4a:	49 8b 87 e8 c5 d0 03 	mov    0x3d0c5e8(%r15),%rax
  3cda51:	66 48 0f 6e c0       	movq   %rax,%xmm0
  3cda56:	31 c0                	xor    %eax,%eax
  3cda58:	41 86 87 80 c5 d0 03 	xchg   %al,0x3d0c580(%r15)
  3cda5f:	48 8b 84 24 d8 02 00 	mov    0x2d8(%rsp),%rax
  3cda66:	00 
  3cda67:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
  3cda6c:	0f 10 8c 24 c8 02 00 	movups 0x2c8(%rsp),%xmm1
  3cda73:	00 
  3cda74:	0f 11 0c 24          	movups %xmm1,(%rsp)
  3cda78:	f3 0f 7e 0d 00 4f 19 	movq   0x194f00(%rip),%xmm1        # 562980 <_ZTS11errorLogger+0x36>
  3cda7f:	00 
  3cda80:	e8 1b 88 de ff       	call   1b62a0 <_ZN3rbk9algorithm16MCLMotionModel2D18setExtraMoveParamsEddNS0_10StateVar2DE@plt>
  3cda85:	48 8d 94 24 a0 02 00 	lea    0x2a0(%rsp),%rdx
  3cda8c:	00 
  3cda8d:	be 03 00 00 00       	mov    $0x3,%esi
  3cda92:	48 8b bc 24 f8 00 00 	mov    0xf8(%rsp),%rdi
  3cda99:	00 
  3cda9a:	e8 51 13 de ff       	call   1aedf0 <_ZN3rbk9algorithm16ParticleFilter2D15ParticlesActionENS1_9Whats2RunERSt6vectorIdSaIdEE@plt>
  3cda9f:	e9 7a e0 ff ff       	jmp    3cbb1e <_ZN5MCLoc20DoNormalUpdateActionEv+0x16de>
  3cdaa4:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cdaa7:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdaaa:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cdaad:	83 f8 01             	cmp    $0x1,%eax
  3cdab0:	0f 85 61 ef ff ff    	jne    3cca17 <_ZN5MCLoc20DoNormalUpdateActionEv+0x25d7>
  3cdab6:	e9 53 ef ff ff       	jmp    3cca0e <_ZN5MCLoc20DoNormalUpdateActionEv+0x25ce>
  3cdabb:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cdabe:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdac1:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cdac4:	83 f8 01             	cmp    $0x1,%eax
  3cdac7:	0f 85 d7 ef ff ff    	jne    3ccaa4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2664>
  3cdacd:	e9 c9 ef ff ff       	jmp    3cca9b <_ZN5MCLoc20DoNormalUpdateActionEv+0x265b>
  3cdad2:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cdad5:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdad8:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cdadb:	83 f8 01             	cmp    $0x1,%eax
  3cdade:	0f 85 4d f0 ff ff    	jne    3ccb31 <_ZN5MCLoc20DoNormalUpdateActionEv+0x26f1>
  3cdae4:	e9 3f f0 ff ff       	jmp    3ccb28 <_ZN5MCLoc20DoNormalUpdateActionEv+0x26e8>
  3cdae9:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cdaec:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdaef:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cdaf2:	83 f8 01             	cmp    $0x1,%eax
  3cdaf5:	0f 85 64 f1 ff ff    	jne    3ccc5f <_ZN5MCLoc20DoNormalUpdateActionEv+0x281f>
  3cdafb:	e9 56 f1 ff ff       	jmp    3ccc56 <_ZN5MCLoc20DoNormalUpdateActionEv+0x2816>
  3cdb00:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cdb03:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdb06:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cdb09:	83 f8 01             	cmp    $0x1,%eax
  3cdb0c:	0f 85 7f f9 ff ff    	jne    3cd491 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3051>
  3cdb12:	e9 71 f9 ff ff       	jmp    3cd488 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3048>
  3cdb17:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cdb1a:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdb1d:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cdb20:	83 f8 01             	cmp    $0x1,%eax
  3cdb23:	0f 85 f5 f9 ff ff    	jne    3cd51e <_ZN5MCLoc20DoNormalUpdateActionEv+0x30de>
  3cdb29:	e9 e7 f9 ff ff       	jmp    3cd515 <_ZN5MCLoc20DoNormalUpdateActionEv+0x30d5>
  3cdb2e:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cdb31:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdb34:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cdb37:	83 f8 01             	cmp    $0x1,%eax
  3cdb3a:	0f 85 6b fa ff ff    	jne    3cd5ab <_ZN5MCLoc20DoNormalUpdateActionEv+0x316b>
  3cdb40:	e9 5d fa ff ff       	jmp    3cd5a2 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3162>
  3cdb45:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cdb48:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdb4b:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cdb4e:	83 f8 01             	cmp    $0x1,%eax
  3cdb51:	0f 85 f8 fa ff ff    	jne    3cd64f <_ZN5MCLoc20DoNormalUpdateActionEv+0x320f>
  3cdb57:	e9 ea fa ff ff       	jmp    3cd646 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3206>
  3cdb5c:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cdb5f:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdb62:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cdb65:	83 f8 01             	cmp    $0x1,%eax
  3cdb68:	0f 85 6c fc ff ff    	jne    3cd7da <_ZN5MCLoc20DoNormalUpdateActionEv+0x339a>
  3cdb6e:	e9 5e fc ff ff       	jmp    3cd7d1 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3391>
  3cdb73:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cdb76:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdb79:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cdb7c:	83 f8 01             	cmp    $0x1,%eax
  3cdb7f:	0f 85 e0 fd ff ff    	jne    3cd965 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3525>
  3cdb85:	e9 d2 fd ff ff       	jmp    3cd95c <_ZN5MCLoc20DoNormalUpdateActionEv+0x351c>
  3cdb8a:	48 89 d8             	mov    %rbx,%rax
  3cdb8d:	48 8d b8 e0 00 00 00 	lea    0xe0(%rax),%rdi
  3cdb94:	48 8d 35 80 68 1f 00 	lea    0x1f6880(%rip),%rsi        # 5c441b <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc15SetGnssParticleERKNS_8protocol12Message_GNSSEE4$_43JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x18b>
  3cdb9b:	48 8d 15 3c 6a 1f 00 	lea    0x1f6a3c(%rip),%rdx        # 5c45de <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc15SetGnssParticleERKNS_8protocol12Message_GNSSEE4$_43JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x34e>
  3cdba2:	48 8d 0d b5 68 1f 00 	lea    0x1f68b5(%rip),%rcx        # 5c445e <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc15SetGnssParticleERKNS_8protocol12Message_GNSSEE4$_43JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1ce>
  3cdba9:	41 b8 fd 01 00 00    	mov    $0x1fd,%r8d
  3cdbaf:	e8 fc 8e de ff       	call   1b6ab0 <_ZN8profiler18SourceLocationDataC1EPKcS2_S2_j@plt>
  3cdbb4:	48 89 d8             	mov    %rbx,%rax
  3cdbb7:	c6 80 e8 00 00 00 01 	movb   $0x1,0xe8(%rax)
  3cdbbe:	e9 b5 c8 ff ff       	jmp    3ca478 <_ZN5MCLoc20DoNormalUpdateActionEv+0x38>
  3cdbc3:	48 8d 3d a7 3d 19 00 	lea    0x193da7(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3cdbca:	e8 f1 92 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3cdbcf:	48 8d 3d 9b 3d 19 00 	lea    0x193d9b(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3cdbd6:	e8 e5 92 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3cdbdb:	89 c7                	mov    %eax,%edi
  3cdbdd:	e8 3e 18 de ff       	call   1af420 <_ZSt20__throw_system_errori@plt>
  3cdbe2:	48 8d 3d 88 3d 19 00 	lea    0x193d88(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3cdbe9:	e8 d2 92 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3cdbee:	48 8d 3d 47 3d 19 00 	lea    0x193d47(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3cdbf5:	e8 86 1e de ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3cdbfa:	48 8d 3d 3b 3d 19 00 	lea    0x193d3b(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3cdc01:	e8 7a 1e de ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3cdc06:	48 8d 3d 2f 3d 19 00 	lea    0x193d2f(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3cdc0d:	e8 6e 1e de ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3cdc12:	48 8d 3d 58 3d 19 00 	lea    0x193d58(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3cdc19:	e8 a2 92 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3cdc1e:	48 8d 3d 4c 3d 19 00 	lea    0x193d4c(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3cdc25:	e8 96 92 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3cdc2a:	48 8d 3d 40 3d 19 00 	lea    0x193d40(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3cdc31:	e8 8a 92 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3cdc36:	48 8d 3d 34 3d 19 00 	lea    0x193d34(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3cdc3d:	e8 7e 92 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3cdc42:	48 8d 3d 28 3d 19 00 	lea    0x193d28(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3cdc49:	e8 72 92 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3cdc4e:	48 8d 3d 1c 3d 19 00 	lea    0x193d1c(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3cdc55:	e8 66 92 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3cdc5a:	48 8d 3d db 3c 19 00 	lea    0x193cdb(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3cdc61:	e8 1a 1e de ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3cdc66:	48 8d 3d cf 3c 19 00 	lea    0x193ccf(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3cdc6d:	e8 0e 1e de ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3cdc72:	48 8d 3d c3 3c 19 00 	lea    0x193cc3(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3cdc79:	e8 02 1e de ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3cdc7e:	48 8d 3d b7 3c 19 00 	lea    0x193cb7(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3cdc85:	e8 f6 1d de ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3cdc8a:	48 8d 3d ab 3c 19 00 	lea    0x193cab(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3cdc91:	e8 ea 1d de ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3cdc96:	48 8d 3d 9f 3c 19 00 	lea    0x193c9f(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3cdc9d:	e8 de 1d de ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3cdca2:	49 89 c6             	mov    %rax,%r14
  3cdca5:	e9 6b 10 00 00       	jmp    3ced15 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48d5>
  3cdcaa:	e9 dd 0b 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3cdcaf:	e9 d8 0b 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3cdcb4:	e9 d3 0b 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3cdcb9:	48 89 c7             	mov    %rax,%rdi
  3cdcbc:	e8 3f 54 df ff       	call   1c3100 <__clang_call_terminate>
  3cdcc1:	48 89 c7             	mov    %rax,%rdi
  3cdcc4:	e8 37 54 df ff       	call   1c3100 <__clang_call_terminate>
  3cdcc9:	48 89 c7             	mov    %rax,%rdi
  3cdccc:	e8 2f 54 df ff       	call   1c3100 <__clang_call_terminate>
  3cdcd1:	48 89 c7             	mov    %rax,%rdi
  3cdcd4:	e8 27 54 df ff       	call   1c3100 <__clang_call_terminate>
  3cdcd9:	48 89 c7             	mov    %rax,%rdi
  3cdcdc:	e8 1f 54 df ff       	call   1c3100 <__clang_call_terminate>
  3cdce1:	48 89 c7             	mov    %rax,%rdi
  3cdce4:	e8 17 54 df ff       	call   1c3100 <__clang_call_terminate>
  3cdce9:	e9 9e 0b 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3cdcee:	e9 99 0b 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3cdcf3:	48 89 c7             	mov    %rax,%rdi
  3cdcf6:	e8 05 54 df ff       	call   1c3100 <__clang_call_terminate>
  3cdcfb:	48 89 c7             	mov    %rax,%rdi
  3cdcfe:	e8 fd 53 df ff       	call   1c3100 <__clang_call_terminate>
  3cdd03:	48 89 c7             	mov    %rax,%rdi
  3cdd06:	e8 f5 53 df ff       	call   1c3100 <__clang_call_terminate>
  3cdd0b:	48 89 c7             	mov    %rax,%rdi
  3cdd0e:	e8 ed 53 df ff       	call   1c3100 <__clang_call_terminate>
  3cdd13:	49 89 c6             	mov    %rax,%r14
  3cdd16:	4d 85 ed             	test   %r13,%r13
  3cdd19:	0f 84 af 03 00 00    	je     3ce0ce <_ZN5MCLoc20DoNormalUpdateActionEv+0x3c8e>
  3cdd1f:	48 83 3d 09 be 52 00 	cmpq   $0x0,0x52be09(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cdd26:	00 
  3cdd27:	74 15                	je     3cdd3e <_ZN5MCLoc20DoNormalUpdateActionEv+0x38fe>
  3cdd29:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cdd2e:	f0 41 0f c1 45 08    	lock xadd %eax,0x8(%r13)
  3cdd34:	83 f8 01             	cmp    $0x1,%eax
  3cdd37:	74 19                	je     3cdd52 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3912>
  3cdd39:	e9 90 03 00 00       	jmp    3ce0ce <_ZN5MCLoc20DoNormalUpdateActionEv+0x3c8e>
  3cdd3e:	41 8b 45 08          	mov    0x8(%r13),%eax
  3cdd42:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdd45:	41 89 4d 08          	mov    %ecx,0x8(%r13)
  3cdd49:	83 f8 01             	cmp    $0x1,%eax
  3cdd4c:	0f 85 7c 03 00 00    	jne    3ce0ce <_ZN5MCLoc20DoNormalUpdateActionEv+0x3c8e>
  3cdd52:	49 8b 45 00          	mov    0x0(%r13),%rax
  3cdd56:	4c 89 ef             	mov    %r13,%rdi
  3cdd59:	ff 50 10             	call   *0x10(%rax)
  3cdd5c:	48 83 3d cc bd 52 00 	cmpq   $0x0,0x52bdcc(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cdd63:	00 
  3cdd64:	74 15                	je     3cdd7b <_ZN5MCLoc20DoNormalUpdateActionEv+0x393b>
  3cdd66:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cdd6b:	f0 41 0f c1 45 0c    	lock xadd %eax,0xc(%r13)
  3cdd71:	83 f8 01             	cmp    $0x1,%eax
  3cdd74:	74 19                	je     3cdd8f <_ZN5MCLoc20DoNormalUpdateActionEv+0x394f>
  3cdd76:	e9 53 03 00 00       	jmp    3ce0ce <_ZN5MCLoc20DoNormalUpdateActionEv+0x3c8e>
  3cdd7b:	41 8b 45 0c          	mov    0xc(%r13),%eax
  3cdd7f:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdd82:	41 89 4d 0c          	mov    %ecx,0xc(%r13)
  3cdd86:	83 f8 01             	cmp    $0x1,%eax
  3cdd89:	0f 85 3f 03 00 00    	jne    3ce0ce <_ZN5MCLoc20DoNormalUpdateActionEv+0x3c8e>
  3cdd8f:	49 8b 45 00          	mov    0x0(%r13),%rax
  3cdd93:	4c 89 ef             	mov    %r13,%rdi
  3cdd96:	ff 50 18             	call   *0x18(%rax)
  3cdd99:	e9 30 03 00 00       	jmp    3ce0ce <_ZN5MCLoc20DoNormalUpdateActionEv+0x3c8e>
  3cdd9e:	49 89 c6             	mov    %rax,%r14
  3cdda1:	4d 85 ed             	test   %r13,%r13
  3cdda4:	0f 84 e6 03 00 00    	je     3ce190 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3d50>
  3cddaa:	48 83 3d 7e bd 52 00 	cmpq   $0x0,0x52bd7e(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cddb1:	00 
  3cddb2:	74 15                	je     3cddc9 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3989>
  3cddb4:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cddb9:	f0 41 0f c1 45 08    	lock xadd %eax,0x8(%r13)
  3cddbf:	83 f8 01             	cmp    $0x1,%eax
  3cddc2:	74 19                	je     3cdddd <_ZN5MCLoc20DoNormalUpdateActionEv+0x399d>
  3cddc4:	e9 c7 03 00 00       	jmp    3ce190 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3d50>
  3cddc9:	41 8b 45 08          	mov    0x8(%r13),%eax
  3cddcd:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cddd0:	41 89 4d 08          	mov    %ecx,0x8(%r13)
  3cddd4:	83 f8 01             	cmp    $0x1,%eax
  3cddd7:	0f 85 b3 03 00 00    	jne    3ce190 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3d50>
  3cdddd:	49 8b 45 00          	mov    0x0(%r13),%rax
  3cdde1:	4c 89 ef             	mov    %r13,%rdi
  3cdde4:	ff 50 10             	call   *0x10(%rax)
  3cdde7:	48 83 3d 41 bd 52 00 	cmpq   $0x0,0x52bd41(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cddee:	00 
  3cddef:	74 15                	je     3cde06 <_ZN5MCLoc20DoNormalUpdateActionEv+0x39c6>
  3cddf1:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cddf6:	f0 41 0f c1 45 0c    	lock xadd %eax,0xc(%r13)
  3cddfc:	83 f8 01             	cmp    $0x1,%eax
  3cddff:	74 19                	je     3cde1a <_ZN5MCLoc20DoNormalUpdateActionEv+0x39da>
  3cde01:	e9 8a 03 00 00       	jmp    3ce190 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3d50>
  3cde06:	41 8b 45 0c          	mov    0xc(%r13),%eax
  3cde0a:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cde0d:	41 89 4d 0c          	mov    %ecx,0xc(%r13)
  3cde11:	83 f8 01             	cmp    $0x1,%eax
  3cde14:	0f 85 76 03 00 00    	jne    3ce190 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3d50>
  3cde1a:	49 8b 45 00          	mov    0x0(%r13),%rax
  3cde1e:	4c 89 ef             	mov    %r13,%rdi
  3cde21:	ff 50 18             	call   *0x18(%rax)
  3cde24:	e9 67 03 00 00       	jmp    3ce190 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3d50>
  3cde29:	49 89 c6             	mov    %rax,%r14
  3cde2c:	4d 85 ed             	test   %r13,%r13
  3cde2f:	0f 84 1d 04 00 00    	je     3ce252 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e12>
  3cde35:	48 83 3d f3 bc 52 00 	cmpq   $0x0,0x52bcf3(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cde3c:	00 
  3cde3d:	74 15                	je     3cde54 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3a14>
  3cde3f:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cde44:	f0 41 0f c1 45 08    	lock xadd %eax,0x8(%r13)
  3cde4a:	83 f8 01             	cmp    $0x1,%eax
  3cde4d:	74 19                	je     3cde68 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3a28>
  3cde4f:	e9 fe 03 00 00       	jmp    3ce252 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e12>
  3cde54:	41 8b 45 08          	mov    0x8(%r13),%eax
  3cde58:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cde5b:	41 89 4d 08          	mov    %ecx,0x8(%r13)
  3cde5f:	83 f8 01             	cmp    $0x1,%eax
  3cde62:	0f 85 ea 03 00 00    	jne    3ce252 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e12>
  3cde68:	49 8b 45 00          	mov    0x0(%r13),%rax
  3cde6c:	4c 89 ef             	mov    %r13,%rdi
  3cde6f:	ff 50 10             	call   *0x10(%rax)
  3cde72:	48 83 3d b6 bc 52 00 	cmpq   $0x0,0x52bcb6(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cde79:	00 
  3cde7a:	74 15                	je     3cde91 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3a51>
  3cde7c:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cde81:	f0 41 0f c1 45 0c    	lock xadd %eax,0xc(%r13)
  3cde87:	83 f8 01             	cmp    $0x1,%eax
  3cde8a:	74 19                	je     3cdea5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3a65>
  3cde8c:	e9 c1 03 00 00       	jmp    3ce252 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e12>
  3cde91:	41 8b 45 0c          	mov    0xc(%r13),%eax
  3cde95:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cde98:	41 89 4d 0c          	mov    %ecx,0xc(%r13)
  3cde9c:	83 f8 01             	cmp    $0x1,%eax
  3cde9f:	0f 85 ad 03 00 00    	jne    3ce252 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e12>
  3cdea5:	49 8b 45 00          	mov    0x0(%r13),%rax
  3cdea9:	4c 89 ef             	mov    %r13,%rdi
  3cdeac:	ff 50 18             	call   *0x18(%rax)
  3cdeaf:	e9 9e 03 00 00       	jmp    3ce252 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e12>
  3cdeb4:	49 89 c6             	mov    %rax,%r14
  3cdeb7:	e9 70 02 00 00       	jmp    3ce12c <_ZN5MCLoc20DoNormalUpdateActionEv+0x3cec>
  3cdebc:	49 89 c6             	mov    %rax,%r14
  3cdebf:	e9 2a 03 00 00       	jmp    3ce1ee <_ZN5MCLoc20DoNormalUpdateActionEv+0x3dae>
  3cdec4:	49 89 c6             	mov    %rax,%r14
  3cdec7:	e9 e4 03 00 00       	jmp    3ce2b0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e70>
  3cdecc:	e9 dc 07 00 00       	jmp    3ce6ad <_ZN5MCLoc20DoNormalUpdateActionEv+0x426d>
  3cded1:	e9 d7 07 00 00       	jmp    3ce6ad <_ZN5MCLoc20DoNormalUpdateActionEv+0x426d>
  3cded6:	e9 d2 07 00 00       	jmp    3ce6ad <_ZN5MCLoc20DoNormalUpdateActionEv+0x426d>
  3cdedb:	e9 ac 09 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3cdee0:	e9 a7 09 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3cdee5:	e9 a2 09 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3cdeea:	e9 9d 09 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3cdeef:	49 89 c6             	mov    %rax,%r14
  3cdef2:	e9 24 0c 00 00       	jmp    3ceb1b <_ZN5MCLoc20DoNormalUpdateActionEv+0x46db>
  3cdef7:	49 89 c6             	mov    %rax,%r14
  3cdefa:	e9 1c 0c 00 00       	jmp    3ceb1b <_ZN5MCLoc20DoNormalUpdateActionEv+0x46db>
  3cdeff:	49 89 c6             	mov    %rax,%r14
  3cdf02:	e9 14 0c 00 00       	jmp    3ceb1b <_ZN5MCLoc20DoNormalUpdateActionEv+0x46db>
  3cdf07:	e9 bf 07 00 00       	jmp    3ce6cb <_ZN5MCLoc20DoNormalUpdateActionEv+0x428b>
  3cdf0c:	e9 ba 07 00 00       	jmp    3ce6cb <_ZN5MCLoc20DoNormalUpdateActionEv+0x428b>
  3cdf11:	e9 b5 07 00 00       	jmp    3ce6cb <_ZN5MCLoc20DoNormalUpdateActionEv+0x428b>
  3cdf16:	e9 cc 07 00 00       	jmp    3ce6e7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x42a7>
  3cdf1b:	e9 c7 07 00 00       	jmp    3ce6e7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x42a7>
  3cdf20:	e9 c2 07 00 00       	jmp    3ce6e7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x42a7>
  3cdf25:	e9 d6 0d 00 00       	jmp    3ced00 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c0>
  3cdf2a:	e9 d1 0d 00 00       	jmp    3ced00 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c0>
  3cdf2f:	e9 cc 0d 00 00       	jmp    3ced00 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c0>
  3cdf34:	48 89 c7             	mov    %rax,%rdi
  3cdf37:	e8 c4 51 df ff       	call   1c3100 <__clang_call_terminate>
  3cdf3c:	48 89 c7             	mov    %rax,%rdi
  3cdf3f:	e8 bc 51 df ff       	call   1c3100 <__clang_call_terminate>
  3cdf44:	49 89 c6             	mov    %rax,%r14
  3cdf47:	4d 85 ed             	test   %r13,%r13
  3cdf4a:	0f 84 78 04 00 00    	je     3ce3c8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f88>
  3cdf50:	48 83 3d d8 bb 52 00 	cmpq   $0x0,0x52bbd8(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cdf57:	00 
  3cdf58:	74 15                	je     3cdf6f <_ZN5MCLoc20DoNormalUpdateActionEv+0x3b2f>
  3cdf5a:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cdf5f:	f0 41 0f c1 45 08    	lock xadd %eax,0x8(%r13)
  3cdf65:	83 f8 01             	cmp    $0x1,%eax
  3cdf68:	74 19                	je     3cdf83 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3b43>
  3cdf6a:	e9 59 04 00 00       	jmp    3ce3c8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f88>
  3cdf6f:	41 8b 45 08          	mov    0x8(%r13),%eax
  3cdf73:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdf76:	41 89 4d 08          	mov    %ecx,0x8(%r13)
  3cdf7a:	83 f8 01             	cmp    $0x1,%eax
  3cdf7d:	0f 85 45 04 00 00    	jne    3ce3c8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f88>
  3cdf83:	49 8b 45 00          	mov    0x0(%r13),%rax
  3cdf87:	4c 89 ef             	mov    %r13,%rdi
  3cdf8a:	ff 50 10             	call   *0x10(%rax)
  3cdf8d:	48 83 3d 9b bb 52 00 	cmpq   $0x0,0x52bb9b(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cdf94:	00 
  3cdf95:	74 15                	je     3cdfac <_ZN5MCLoc20DoNormalUpdateActionEv+0x3b6c>
  3cdf97:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cdf9c:	f0 41 0f c1 45 0c    	lock xadd %eax,0xc(%r13)
  3cdfa2:	83 f8 01             	cmp    $0x1,%eax
  3cdfa5:	74 19                	je     3cdfc0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3b80>
  3cdfa7:	e9 1c 04 00 00       	jmp    3ce3c8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f88>
  3cdfac:	41 8b 45 0c          	mov    0xc(%r13),%eax
  3cdfb0:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cdfb3:	41 89 4d 0c          	mov    %ecx,0xc(%r13)
  3cdfb7:	83 f8 01             	cmp    $0x1,%eax
  3cdfba:	0f 85 08 04 00 00    	jne    3ce3c8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f88>
  3cdfc0:	49 8b 45 00          	mov    0x0(%r13),%rax
  3cdfc4:	4c 89 ef             	mov    %r13,%rdi
  3cdfc7:	ff 50 18             	call   *0x18(%rax)
  3cdfca:	e9 f9 03 00 00       	jmp    3ce3c8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f88>
  3cdfcf:	49 89 c6             	mov    %rax,%r14
  3cdfd2:	4d 85 ed             	test   %r13,%r13
  3cdfd5:	0f 84 b4 04 00 00    	je     3ce48f <_ZN5MCLoc20DoNormalUpdateActionEv+0x404f>
  3cdfdb:	48 83 3d 4d bb 52 00 	cmpq   $0x0,0x52bb4d(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cdfe2:	00 
  3cdfe3:	74 15                	je     3cdffa <_ZN5MCLoc20DoNormalUpdateActionEv+0x3bba>
  3cdfe5:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cdfea:	f0 41 0f c1 45 08    	lock xadd %eax,0x8(%r13)
  3cdff0:	83 f8 01             	cmp    $0x1,%eax
  3cdff3:	74 19                	je     3ce00e <_ZN5MCLoc20DoNormalUpdateActionEv+0x3bce>
  3cdff5:	e9 95 04 00 00       	jmp    3ce48f <_ZN5MCLoc20DoNormalUpdateActionEv+0x404f>
  3cdffa:	41 8b 45 08          	mov    0x8(%r13),%eax
  3cdffe:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce001:	41 89 4d 08          	mov    %ecx,0x8(%r13)
  3ce005:	83 f8 01             	cmp    $0x1,%eax
  3ce008:	0f 85 81 04 00 00    	jne    3ce48f <_ZN5MCLoc20DoNormalUpdateActionEv+0x404f>
  3ce00e:	49 8b 45 00          	mov    0x0(%r13),%rax
  3ce012:	4c 89 ef             	mov    %r13,%rdi
  3ce015:	ff 50 10             	call   *0x10(%rax)
  3ce018:	48 83 3d 10 bb 52 00 	cmpq   $0x0,0x52bb10(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce01f:	00 
  3ce020:	74 15                	je     3ce037 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3bf7>
  3ce022:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce027:	f0 41 0f c1 45 0c    	lock xadd %eax,0xc(%r13)
  3ce02d:	83 f8 01             	cmp    $0x1,%eax
  3ce030:	74 19                	je     3ce04b <_ZN5MCLoc20DoNormalUpdateActionEv+0x3c0b>
  3ce032:	e9 58 04 00 00       	jmp    3ce48f <_ZN5MCLoc20DoNormalUpdateActionEv+0x404f>
  3ce037:	41 8b 45 0c          	mov    0xc(%r13),%eax
  3ce03b:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce03e:	41 89 4d 0c          	mov    %ecx,0xc(%r13)
  3ce042:	83 f8 01             	cmp    $0x1,%eax
  3ce045:	0f 85 44 04 00 00    	jne    3ce48f <_ZN5MCLoc20DoNormalUpdateActionEv+0x404f>
  3ce04b:	49 8b 45 00          	mov    0x0(%r13),%rax
  3ce04f:	4c 89 ef             	mov    %r13,%rdi
  3ce052:	ff 50 18             	call   *0x18(%rax)
  3ce055:	e9 35 04 00 00       	jmp    3ce48f <_ZN5MCLoc20DoNormalUpdateActionEv+0x404f>
  3ce05a:	49 89 c6             	mov    %rax,%r14
  3ce05d:	e9 70 03 00 00       	jmp    3ce3d2 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f92>
  3ce062:	49 89 c6             	mov    %rax,%r14
  3ce065:	e9 2f 04 00 00       	jmp    3ce499 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4059>
  3ce06a:	e9 3e 06 00 00       	jmp    3ce6ad <_ZN5MCLoc20DoNormalUpdateActionEv+0x426d>
  3ce06f:	e9 39 06 00 00       	jmp    3ce6ad <_ZN5MCLoc20DoNormalUpdateActionEv+0x426d>
  3ce074:	e9 13 08 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3ce079:	e9 0e 08 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3ce07e:	49 89 c6             	mov    %rax,%r14
  3ce081:	e9 95 0a 00 00       	jmp    3ceb1b <_ZN5MCLoc20DoNormalUpdateActionEv+0x46db>
  3ce086:	49 89 c6             	mov    %rax,%r14
  3ce089:	e9 8d 0a 00 00       	jmp    3ceb1b <_ZN5MCLoc20DoNormalUpdateActionEv+0x46db>
  3ce08e:	e9 38 06 00 00       	jmp    3ce6cb <_ZN5MCLoc20DoNormalUpdateActionEv+0x428b>
  3ce093:	e9 33 06 00 00       	jmp    3ce6cb <_ZN5MCLoc20DoNormalUpdateActionEv+0x428b>
  3ce098:	e9 4a 06 00 00       	jmp    3ce6e7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x42a7>
  3ce09d:	e9 45 06 00 00       	jmp    3ce6e7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x42a7>
  3ce0a2:	e9 59 0c 00 00       	jmp    3ced00 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c0>
  3ce0a7:	e9 54 0c 00 00       	jmp    3ced00 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c0>
  3ce0ac:	49 89 c6             	mov    %rax,%r14
  3ce0af:	48 8b 8c 24 b0 00 00 	mov    0xb0(%rsp),%rcx
  3ce0b6:	00 
  3ce0b7:	48 85 c9             	test   %rcx,%rcx
  3ce0ba:	74 12                	je     3ce0ce <_ZN5MCLoc20DoNormalUpdateActionEv+0x3c8e>
  3ce0bc:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3ce0c3:	00 
  3ce0c4:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce0c9:	48 89 fe             	mov    %rdi,%rsi
  3ce0cc:	ff d1                	call   *%rcx
  3ce0ce:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3ce0d3:	48 85 db             	test   %rbx,%rbx
  3ce0d6:	74 54                	je     3ce12c <_ZN5MCLoc20DoNormalUpdateActionEv+0x3cec>
  3ce0d8:	48 83 3d 50 ba 52 00 	cmpq   $0x0,0x52ba50(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce0df:	00 
  3ce0e0:	74 11                	je     3ce0f3 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3cb3>
  3ce0e2:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce0e7:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3ce0ec:	83 f8 01             	cmp    $0x1,%eax
  3ce0ef:	74 10                	je     3ce101 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3cc1>
  3ce0f1:	eb 39                	jmp    3ce12c <_ZN5MCLoc20DoNormalUpdateActionEv+0x3cec>
  3ce0f3:	8b 43 08             	mov    0x8(%rbx),%eax
  3ce0f6:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce0f9:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3ce0fc:	83 f8 01             	cmp    $0x1,%eax
  3ce0ff:	75 2b                	jne    3ce12c <_ZN5MCLoc20DoNormalUpdateActionEv+0x3cec>
  3ce101:	48 8b 03             	mov    (%rbx),%rax
  3ce104:	48 89 df             	mov    %rbx,%rdi
  3ce107:	ff 50 10             	call   *0x10(%rax)
  3ce10a:	48 83 3d 1e ba 52 00 	cmpq   $0x0,0x52ba1e(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce111:	00 
  3ce112:	74 3a                	je     3ce14e <_ZN5MCLoc20DoNormalUpdateActionEv+0x3d0e>
  3ce114:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce119:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3ce11e:	83 f8 01             	cmp    $0x1,%eax
  3ce121:	75 09                	jne    3ce12c <_ZN5MCLoc20DoNormalUpdateActionEv+0x3cec>
  3ce123:	48 8b 03             	mov    (%rbx),%rax
  3ce126:	48 89 df             	mov    %rbx,%rdi
  3ce129:	ff 50 18             	call   *0x18(%rax)
  3ce12c:	48 8b 4c 24 68       	mov    0x68(%rsp),%rcx
  3ce131:	48 85 c9             	test   %rcx,%rcx
  3ce134:	0f 84 b3 09 00 00    	je     3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce13a:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3ce13f:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce144:	48 89 fe             	mov    %rdi,%rsi
  3ce147:	ff d1                	call   *%rcx
  3ce149:	e9 9f 09 00 00       	jmp    3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce14e:	8b 43 0c             	mov    0xc(%rbx),%eax
  3ce151:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce154:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3ce157:	83 f8 01             	cmp    $0x1,%eax
  3ce15a:	75 d0                	jne    3ce12c <_ZN5MCLoc20DoNormalUpdateActionEv+0x3cec>
  3ce15c:	eb c5                	jmp    3ce123 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3ce3>
  3ce15e:	48 89 c7             	mov    %rax,%rdi
  3ce161:	e8 9a 4f df ff       	call   1c3100 <__clang_call_terminate>
  3ce166:	48 89 c7             	mov    %rax,%rdi
  3ce169:	e8 92 4f df ff       	call   1c3100 <__clang_call_terminate>
  3ce16e:	49 89 c6             	mov    %rax,%r14
  3ce171:	48 8b 8c 24 b0 00 00 	mov    0xb0(%rsp),%rcx
  3ce178:	00 
  3ce179:	48 85 c9             	test   %rcx,%rcx
  3ce17c:	74 12                	je     3ce190 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3d50>
  3ce17e:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3ce185:	00 
  3ce186:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce18b:	48 89 fe             	mov    %rdi,%rsi
  3ce18e:	ff d1                	call   *%rcx
  3ce190:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3ce195:	48 85 db             	test   %rbx,%rbx
  3ce198:	74 54                	je     3ce1ee <_ZN5MCLoc20DoNormalUpdateActionEv+0x3dae>
  3ce19a:	48 83 3d 8e b9 52 00 	cmpq   $0x0,0x52b98e(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce1a1:	00 
  3ce1a2:	74 11                	je     3ce1b5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3d75>
  3ce1a4:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce1a9:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3ce1ae:	83 f8 01             	cmp    $0x1,%eax
  3ce1b1:	74 10                	je     3ce1c3 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3d83>
  3ce1b3:	eb 39                	jmp    3ce1ee <_ZN5MCLoc20DoNormalUpdateActionEv+0x3dae>
  3ce1b5:	8b 43 08             	mov    0x8(%rbx),%eax
  3ce1b8:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce1bb:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3ce1be:	83 f8 01             	cmp    $0x1,%eax
  3ce1c1:	75 2b                	jne    3ce1ee <_ZN5MCLoc20DoNormalUpdateActionEv+0x3dae>
  3ce1c3:	48 8b 03             	mov    (%rbx),%rax
  3ce1c6:	48 89 df             	mov    %rbx,%rdi
  3ce1c9:	ff 50 10             	call   *0x10(%rax)
  3ce1cc:	48 83 3d 5c b9 52 00 	cmpq   $0x0,0x52b95c(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce1d3:	00 
  3ce1d4:	74 3a                	je     3ce210 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3dd0>
  3ce1d6:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce1db:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3ce1e0:	83 f8 01             	cmp    $0x1,%eax
  3ce1e3:	75 09                	jne    3ce1ee <_ZN5MCLoc20DoNormalUpdateActionEv+0x3dae>
  3ce1e5:	48 8b 03             	mov    (%rbx),%rax
  3ce1e8:	48 89 df             	mov    %rbx,%rdi
  3ce1eb:	ff 50 18             	call   *0x18(%rax)
  3ce1ee:	48 8b 4c 24 68       	mov    0x68(%rsp),%rcx
  3ce1f3:	48 85 c9             	test   %rcx,%rcx
  3ce1f6:	0f 84 f1 08 00 00    	je     3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce1fc:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3ce201:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce206:	48 89 fe             	mov    %rdi,%rsi
  3ce209:	ff d1                	call   *%rcx
  3ce20b:	e9 dd 08 00 00       	jmp    3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce210:	8b 43 0c             	mov    0xc(%rbx),%eax
  3ce213:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce216:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3ce219:	83 f8 01             	cmp    $0x1,%eax
  3ce21c:	75 d0                	jne    3ce1ee <_ZN5MCLoc20DoNormalUpdateActionEv+0x3dae>
  3ce21e:	eb c5                	jmp    3ce1e5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3da5>
  3ce220:	48 89 c7             	mov    %rax,%rdi
  3ce223:	e8 d8 4e df ff       	call   1c3100 <__clang_call_terminate>
  3ce228:	48 89 c7             	mov    %rax,%rdi
  3ce22b:	e8 d0 4e df ff       	call   1c3100 <__clang_call_terminate>
  3ce230:	49 89 c6             	mov    %rax,%r14
  3ce233:	48 8b 8c 24 b0 00 00 	mov    0xb0(%rsp),%rcx
  3ce23a:	00 
  3ce23b:	48 85 c9             	test   %rcx,%rcx
  3ce23e:	74 12                	je     3ce252 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e12>
  3ce240:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3ce247:	00 
  3ce248:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce24d:	48 89 fe             	mov    %rdi,%rsi
  3ce250:	ff d1                	call   *%rcx
  3ce252:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3ce257:	48 85 db             	test   %rbx,%rbx
  3ce25a:	74 54                	je     3ce2b0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e70>
  3ce25c:	48 83 3d cc b8 52 00 	cmpq   $0x0,0x52b8cc(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce263:	00 
  3ce264:	74 11                	je     3ce277 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e37>
  3ce266:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce26b:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3ce270:	83 f8 01             	cmp    $0x1,%eax
  3ce273:	74 10                	je     3ce285 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e45>
  3ce275:	eb 39                	jmp    3ce2b0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e70>
  3ce277:	8b 43 08             	mov    0x8(%rbx),%eax
  3ce27a:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce27d:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3ce280:	83 f8 01             	cmp    $0x1,%eax
  3ce283:	75 2b                	jne    3ce2b0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e70>
  3ce285:	48 8b 03             	mov    (%rbx),%rax
  3ce288:	48 89 df             	mov    %rbx,%rdi
  3ce28b:	ff 50 10             	call   *0x10(%rax)
  3ce28e:	48 83 3d 9a b8 52 00 	cmpq   $0x0,0x52b89a(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce295:	00 
  3ce296:	74 3a                	je     3ce2d2 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e92>
  3ce298:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce29d:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3ce2a2:	83 f8 01             	cmp    $0x1,%eax
  3ce2a5:	75 09                	jne    3ce2b0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e70>
  3ce2a7:	48 8b 03             	mov    (%rbx),%rax
  3ce2aa:	48 89 df             	mov    %rbx,%rdi
  3ce2ad:	ff 50 18             	call   *0x18(%rax)
  3ce2b0:	48 8b 4c 24 68       	mov    0x68(%rsp),%rcx
  3ce2b5:	48 85 c9             	test   %rcx,%rcx
  3ce2b8:	0f 84 2f 08 00 00    	je     3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce2be:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3ce2c3:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce2c8:	48 89 fe             	mov    %rdi,%rsi
  3ce2cb:	ff d1                	call   *%rcx
  3ce2cd:	e9 1b 08 00 00       	jmp    3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce2d2:	8b 43 0c             	mov    0xc(%rbx),%eax
  3ce2d5:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce2d8:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3ce2db:	83 f8 01             	cmp    $0x1,%eax
  3ce2de:	75 d0                	jne    3ce2b0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e70>
  3ce2e0:	eb c5                	jmp    3ce2a7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3e67>
  3ce2e2:	48 89 c7             	mov    %rax,%rdi
  3ce2e5:	e8 16 4e df ff       	call   1c3100 <__clang_call_terminate>
  3ce2ea:	48 89 c7             	mov    %rax,%rdi
  3ce2ed:	e8 0e 4e df ff       	call   1c3100 <__clang_call_terminate>
  3ce2f2:	49 89 c6             	mov    %rax,%r14
  3ce2f5:	4d 85 ed             	test   %r13,%r13
  3ce2f8:	0f 84 6d 02 00 00    	je     3ce56b <_ZN5MCLoc20DoNormalUpdateActionEv+0x412b>
  3ce2fe:	48 83 3d 2a b8 52 00 	cmpq   $0x0,0x52b82a(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce305:	00 
  3ce306:	74 15                	je     3ce31d <_ZN5MCLoc20DoNormalUpdateActionEv+0x3edd>
  3ce308:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce30d:	f0 41 0f c1 45 08    	lock xadd %eax,0x8(%r13)
  3ce313:	83 f8 01             	cmp    $0x1,%eax
  3ce316:	74 19                	je     3ce331 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3ef1>
  3ce318:	e9 4e 02 00 00       	jmp    3ce56b <_ZN5MCLoc20DoNormalUpdateActionEv+0x412b>
  3ce31d:	41 8b 45 08          	mov    0x8(%r13),%eax
  3ce321:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce324:	41 89 4d 08          	mov    %ecx,0x8(%r13)
  3ce328:	83 f8 01             	cmp    $0x1,%eax
  3ce32b:	0f 85 3a 02 00 00    	jne    3ce56b <_ZN5MCLoc20DoNormalUpdateActionEv+0x412b>
  3ce331:	49 8b 45 00          	mov    0x0(%r13),%rax
  3ce335:	4c 89 ef             	mov    %r13,%rdi
  3ce338:	ff 50 10             	call   *0x10(%rax)
  3ce33b:	48 83 3d ed b7 52 00 	cmpq   $0x0,0x52b7ed(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce342:	00 
  3ce343:	74 15                	je     3ce35a <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f1a>
  3ce345:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce34a:	f0 41 0f c1 45 0c    	lock xadd %eax,0xc(%r13)
  3ce350:	83 f8 01             	cmp    $0x1,%eax
  3ce353:	74 19                	je     3ce36e <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f2e>
  3ce355:	e9 11 02 00 00       	jmp    3ce56b <_ZN5MCLoc20DoNormalUpdateActionEv+0x412b>
  3ce35a:	41 8b 45 0c          	mov    0xc(%r13),%eax
  3ce35e:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce361:	41 89 4d 0c          	mov    %ecx,0xc(%r13)
  3ce365:	83 f8 01             	cmp    $0x1,%eax
  3ce368:	0f 85 fd 01 00 00    	jne    3ce56b <_ZN5MCLoc20DoNormalUpdateActionEv+0x412b>
  3ce36e:	49 8b 45 00          	mov    0x0(%r13),%rax
  3ce372:	4c 89 ef             	mov    %r13,%rdi
  3ce375:	ff 50 18             	call   *0x18(%rax)
  3ce378:	e9 ee 01 00 00       	jmp    3ce56b <_ZN5MCLoc20DoNormalUpdateActionEv+0x412b>
  3ce37d:	49 89 c6             	mov    %rax,%r14
  3ce380:	e9 f0 01 00 00       	jmp    3ce575 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4135>
  3ce385:	e9 23 03 00 00       	jmp    3ce6ad <_ZN5MCLoc20DoNormalUpdateActionEv+0x426d>
  3ce38a:	e9 fd 04 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3ce38f:	49 89 c6             	mov    %rax,%r14
  3ce392:	e9 84 07 00 00       	jmp    3ceb1b <_ZN5MCLoc20DoNormalUpdateActionEv+0x46db>
  3ce397:	e9 2f 03 00 00       	jmp    3ce6cb <_ZN5MCLoc20DoNormalUpdateActionEv+0x428b>
  3ce39c:	e9 46 03 00 00       	jmp    3ce6e7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x42a7>
  3ce3a1:	e9 5a 09 00 00       	jmp    3ced00 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c0>
  3ce3a6:	49 89 c6             	mov    %rax,%r14
  3ce3a9:	48 8b 8c 24 b0 00 00 	mov    0xb0(%rsp),%rcx
  3ce3b0:	00 
  3ce3b1:	48 85 c9             	test   %rcx,%rcx
  3ce3b4:	74 12                	je     3ce3c8 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f88>
  3ce3b6:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3ce3bd:	00 
  3ce3be:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce3c3:	48 89 fe             	mov    %rdi,%rsi
  3ce3c6:	ff d1                	call   *%rcx
  3ce3c8:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3ce3cd:	48 85 db             	test   %rbx,%rbx
  3ce3d0:	75 22                	jne    3ce3f4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3fb4>
  3ce3d2:	48 8b 4c 24 68       	mov    0x68(%rsp),%rcx
  3ce3d7:	48 85 c9             	test   %rcx,%rcx
  3ce3da:	0f 84 0d 07 00 00    	je     3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce3e0:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3ce3e5:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce3ea:	48 89 fe             	mov    %rdi,%rsi
  3ce3ed:	ff d1                	call   *%rcx
  3ce3ef:	e9 f9 06 00 00       	jmp    3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce3f4:	48 83 3d 34 b7 52 00 	cmpq   $0x0,0x52b734(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce3fb:	00 
  3ce3fc:	74 11                	je     3ce40f <_ZN5MCLoc20DoNormalUpdateActionEv+0x3fcf>
  3ce3fe:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce403:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3ce408:	83 f8 01             	cmp    $0x1,%eax
  3ce40b:	74 10                	je     3ce41d <_ZN5MCLoc20DoNormalUpdateActionEv+0x3fdd>
  3ce40d:	eb c3                	jmp    3ce3d2 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f92>
  3ce40f:	8b 43 08             	mov    0x8(%rbx),%eax
  3ce412:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce415:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3ce418:	83 f8 01             	cmp    $0x1,%eax
  3ce41b:	75 b5                	jne    3ce3d2 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f92>
  3ce41d:	48 8b 03             	mov    (%rbx),%rax
  3ce420:	48 89 df             	mov    %rbx,%rdi
  3ce423:	ff 50 10             	call   *0x10(%rax)
  3ce426:	48 83 3d 02 b7 52 00 	cmpq   $0x0,0x52b702(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce42d:	00 
  3ce42e:	74 11                	je     3ce441 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4001>
  3ce430:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce435:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3ce43a:	83 f8 01             	cmp    $0x1,%eax
  3ce43d:	74 10                	je     3ce44f <_ZN5MCLoc20DoNormalUpdateActionEv+0x400f>
  3ce43f:	eb 91                	jmp    3ce3d2 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f92>
  3ce441:	8b 43 0c             	mov    0xc(%rbx),%eax
  3ce444:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce447:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3ce44a:	83 f8 01             	cmp    $0x1,%eax
  3ce44d:	75 83                	jne    3ce3d2 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f92>
  3ce44f:	48 8b 03             	mov    (%rbx),%rax
  3ce452:	48 89 df             	mov    %rbx,%rdi
  3ce455:	ff 50 18             	call   *0x18(%rax)
  3ce458:	e9 75 ff ff ff       	jmp    3ce3d2 <_ZN5MCLoc20DoNormalUpdateActionEv+0x3f92>
  3ce45d:	48 89 c7             	mov    %rax,%rdi
  3ce460:	e8 9b 4c df ff       	call   1c3100 <__clang_call_terminate>
  3ce465:	48 89 c7             	mov    %rax,%rdi
  3ce468:	e8 93 4c df ff       	call   1c3100 <__clang_call_terminate>
  3ce46d:	49 89 c6             	mov    %rax,%r14
  3ce470:	48 8b 8c 24 b0 00 00 	mov    0xb0(%rsp),%rcx
  3ce477:	00 
  3ce478:	48 85 c9             	test   %rcx,%rcx
  3ce47b:	74 12                	je     3ce48f <_ZN5MCLoc20DoNormalUpdateActionEv+0x404f>
  3ce47d:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3ce484:	00 
  3ce485:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce48a:	48 89 fe             	mov    %rdi,%rsi
  3ce48d:	ff d1                	call   *%rcx
  3ce48f:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3ce494:	48 85 db             	test   %rbx,%rbx
  3ce497:	75 22                	jne    3ce4bb <_ZN5MCLoc20DoNormalUpdateActionEv+0x407b>
  3ce499:	48 8b 4c 24 68       	mov    0x68(%rsp),%rcx
  3ce49e:	48 85 c9             	test   %rcx,%rcx
  3ce4a1:	0f 84 46 06 00 00    	je     3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce4a7:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3ce4ac:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce4b1:	48 89 fe             	mov    %rdi,%rsi
  3ce4b4:	ff d1                	call   *%rcx
  3ce4b6:	e9 32 06 00 00       	jmp    3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce4bb:	48 83 3d 6d b6 52 00 	cmpq   $0x0,0x52b66d(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce4c2:	00 
  3ce4c3:	74 11                	je     3ce4d6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4096>
  3ce4c5:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce4ca:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3ce4cf:	83 f8 01             	cmp    $0x1,%eax
  3ce4d2:	74 10                	je     3ce4e4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x40a4>
  3ce4d4:	eb c3                	jmp    3ce499 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4059>
  3ce4d6:	8b 43 08             	mov    0x8(%rbx),%eax
  3ce4d9:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce4dc:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3ce4df:	83 f8 01             	cmp    $0x1,%eax
  3ce4e2:	75 b5                	jne    3ce499 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4059>
  3ce4e4:	48 8b 03             	mov    (%rbx),%rax
  3ce4e7:	48 89 df             	mov    %rbx,%rdi
  3ce4ea:	ff 50 10             	call   *0x10(%rax)
  3ce4ed:	48 83 3d 3b b6 52 00 	cmpq   $0x0,0x52b63b(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce4f4:	00 
  3ce4f5:	74 11                	je     3ce508 <_ZN5MCLoc20DoNormalUpdateActionEv+0x40c8>
  3ce4f7:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce4fc:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3ce501:	83 f8 01             	cmp    $0x1,%eax
  3ce504:	74 10                	je     3ce516 <_ZN5MCLoc20DoNormalUpdateActionEv+0x40d6>
  3ce506:	eb 91                	jmp    3ce499 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4059>
  3ce508:	8b 43 0c             	mov    0xc(%rbx),%eax
  3ce50b:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce50e:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3ce511:	83 f8 01             	cmp    $0x1,%eax
  3ce514:	75 83                	jne    3ce499 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4059>
  3ce516:	48 8b 03             	mov    (%rbx),%rax
  3ce519:	48 89 df             	mov    %rbx,%rdi
  3ce51c:	ff 50 18             	call   *0x18(%rax)
  3ce51f:	e9 75 ff ff ff       	jmp    3ce499 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4059>
  3ce524:	48 89 c7             	mov    %rax,%rdi
  3ce527:	e8 d4 4b df ff       	call   1c3100 <__clang_call_terminate>
  3ce52c:	48 89 c7             	mov    %rax,%rdi
  3ce52f:	e8 cc 4b df ff       	call   1c3100 <__clang_call_terminate>
  3ce534:	e9 53 03 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3ce539:	48 89 c7             	mov    %rax,%rdi
  3ce53c:	e8 bf 4b df ff       	call   1c3100 <__clang_call_terminate>
  3ce541:	48 89 c7             	mov    %rax,%rdi
  3ce544:	e8 b7 4b df ff       	call   1c3100 <__clang_call_terminate>
  3ce549:	49 89 c6             	mov    %rax,%r14
  3ce54c:	48 8b 8c 24 b0 00 00 	mov    0xb0(%rsp),%rcx
  3ce553:	00 
  3ce554:	48 85 c9             	test   %rcx,%rcx
  3ce557:	74 12                	je     3ce56b <_ZN5MCLoc20DoNormalUpdateActionEv+0x412b>
  3ce559:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3ce560:	00 
  3ce561:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce566:	48 89 fe             	mov    %rdi,%rsi
  3ce569:	ff d1                	call   *%rcx
  3ce56b:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3ce570:	48 85 db             	test   %rbx,%rbx
  3ce573:	75 22                	jne    3ce597 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4157>
  3ce575:	48 8b 4c 24 68       	mov    0x68(%rsp),%rcx
  3ce57a:	48 85 c9             	test   %rcx,%rcx
  3ce57d:	0f 84 6a 05 00 00    	je     3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce583:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3ce588:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce58d:	48 89 fe             	mov    %rdi,%rsi
  3ce590:	ff d1                	call   *%rcx
  3ce592:	e9 56 05 00 00       	jmp    3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce597:	48 83 3d 91 b5 52 00 	cmpq   $0x0,0x52b591(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce59e:	00 
  3ce59f:	74 11                	je     3ce5b2 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4172>
  3ce5a1:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce5a6:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3ce5ab:	83 f8 01             	cmp    $0x1,%eax
  3ce5ae:	74 10                	je     3ce5c0 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4180>
  3ce5b0:	eb c3                	jmp    3ce575 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4135>
  3ce5b2:	8b 43 08             	mov    0x8(%rbx),%eax
  3ce5b5:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce5b8:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3ce5bb:	83 f8 01             	cmp    $0x1,%eax
  3ce5be:	75 b5                	jne    3ce575 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4135>
  3ce5c0:	48 8b 03             	mov    (%rbx),%rax
  3ce5c3:	48 89 df             	mov    %rbx,%rdi
  3ce5c6:	ff 50 10             	call   *0x10(%rax)
  3ce5c9:	48 83 3d 5f b5 52 00 	cmpq   $0x0,0x52b55f(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce5d0:	00 
  3ce5d1:	74 11                	je     3ce5e4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x41a4>
  3ce5d3:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce5d8:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3ce5dd:	83 f8 01             	cmp    $0x1,%eax
  3ce5e0:	74 10                	je     3ce5f2 <_ZN5MCLoc20DoNormalUpdateActionEv+0x41b2>
  3ce5e2:	eb 91                	jmp    3ce575 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4135>
  3ce5e4:	8b 43 0c             	mov    0xc(%rbx),%eax
  3ce5e7:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce5ea:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3ce5ed:	83 f8 01             	cmp    $0x1,%eax
  3ce5f0:	75 83                	jne    3ce575 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4135>
  3ce5f2:	48 8b 03             	mov    (%rbx),%rax
  3ce5f5:	48 89 df             	mov    %rbx,%rdi
  3ce5f8:	ff 50 18             	call   *0x18(%rax)
  3ce5fb:	e9 75 ff ff ff       	jmp    3ce575 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4135>
  3ce600:	48 89 c7             	mov    %rax,%rdi
  3ce603:	e8 f8 4a df ff       	call   1c3100 <__clang_call_terminate>
  3ce608:	48 89 c7             	mov    %rax,%rdi
  3ce60b:	e8 f0 4a df ff       	call   1c3100 <__clang_call_terminate>
  3ce610:	e9 b9 01 00 00       	jmp    3ce7ce <_ZN5MCLoc20DoNormalUpdateActionEv+0x438e>
  3ce615:	e9 72 02 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3ce61a:	49 89 c6             	mov    %rax,%r14
  3ce61d:	4d 85 ed             	test   %r13,%r13
  3ce620:	0f 84 a5 02 00 00    	je     3ce8cb <_ZN5MCLoc20DoNormalUpdateActionEv+0x448b>
  3ce626:	48 83 3d 02 b5 52 00 	cmpq   $0x0,0x52b502(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce62d:	00 
  3ce62e:	74 15                	je     3ce645 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4205>
  3ce630:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce635:	f0 41 0f c1 45 08    	lock xadd %eax,0x8(%r13)
  3ce63b:	83 f8 01             	cmp    $0x1,%eax
  3ce63e:	74 19                	je     3ce659 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4219>
  3ce640:	e9 86 02 00 00       	jmp    3ce8cb <_ZN5MCLoc20DoNormalUpdateActionEv+0x448b>
  3ce645:	41 8b 45 08          	mov    0x8(%r13),%eax
  3ce649:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce64c:	41 89 4d 08          	mov    %ecx,0x8(%r13)
  3ce650:	83 f8 01             	cmp    $0x1,%eax
  3ce653:	0f 85 72 02 00 00    	jne    3ce8cb <_ZN5MCLoc20DoNormalUpdateActionEv+0x448b>
  3ce659:	49 8b 45 00          	mov    0x0(%r13),%rax
  3ce65d:	4c 89 ef             	mov    %r13,%rdi
  3ce660:	ff 50 10             	call   *0x10(%rax)
  3ce663:	48 83 3d c5 b4 52 00 	cmpq   $0x0,0x52b4c5(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce66a:	00 
  3ce66b:	74 15                	je     3ce682 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4242>
  3ce66d:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce672:	f0 41 0f c1 45 0c    	lock xadd %eax,0xc(%r13)
  3ce678:	83 f8 01             	cmp    $0x1,%eax
  3ce67b:	74 19                	je     3ce696 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4256>
  3ce67d:	e9 49 02 00 00       	jmp    3ce8cb <_ZN5MCLoc20DoNormalUpdateActionEv+0x448b>
  3ce682:	41 8b 45 0c          	mov    0xc(%r13),%eax
  3ce686:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce689:	41 89 4d 0c          	mov    %ecx,0xc(%r13)
  3ce68d:	83 f8 01             	cmp    $0x1,%eax
  3ce690:	0f 85 35 02 00 00    	jne    3ce8cb <_ZN5MCLoc20DoNormalUpdateActionEv+0x448b>
  3ce696:	49 8b 45 00          	mov    0x0(%r13),%rax
  3ce69a:	4c 89 ef             	mov    %r13,%rdi
  3ce69d:	ff 50 18             	call   *0x18(%rax)
  3ce6a0:	e9 26 02 00 00       	jmp    3ce8cb <_ZN5MCLoc20DoNormalUpdateActionEv+0x448b>
  3ce6a5:	49 89 c6             	mov    %rax,%r14
  3ce6a8:	e9 28 02 00 00       	jmp    3ce8d5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4495>
  3ce6ad:	49 89 c6             	mov    %rax,%r14
  3ce6b0:	4c 39 fb             	cmp    %r15,%rbx
  3ce6b3:	0f 84 34 04 00 00    	je     3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce6b9:	e9 c1 01 00 00       	jmp    3ce87f <_ZN5MCLoc20DoNormalUpdateActionEv+0x443f>
  3ce6be:	e9 c9 01 00 00       	jmp    3ce88c <_ZN5MCLoc20DoNormalUpdateActionEv+0x444c>
  3ce6c3:	49 89 c6             	mov    %rax,%r14
  3ce6c6:	e9 50 04 00 00       	jmp    3ceb1b <_ZN5MCLoc20DoNormalUpdateActionEv+0x46db>
  3ce6cb:	49 89 c6             	mov    %rax,%r14
  3ce6ce:	48 8b 7c 24 78       	mov    0x78(%rsp),%rdi
  3ce6d3:	48 8d 84 24 88 00 00 	lea    0x88(%rsp),%rax
  3ce6da:	00 
  3ce6db:	48 39 c7             	cmp    %rax,%rdi
  3ce6de:	74 0a                	je     3ce6ea <_ZN5MCLoc20DoNormalUpdateActionEv+0x42aa>
  3ce6e0:	e8 0b 12 de ff       	call   1af8f0 <_ZdlPv@plt>
  3ce6e5:	eb 03                	jmp    3ce6ea <_ZN5MCLoc20DoNormalUpdateActionEv+0x42aa>
  3ce6e7:	49 89 c6             	mov    %rax,%r14
  3ce6ea:	48 8b 7c 24 58       	mov    0x58(%rsp),%rdi
  3ce6ef:	48 39 df             	cmp    %rbx,%rdi
  3ce6f2:	0f 85 1e 04 00 00    	jne    3ceb16 <_ZN5MCLoc20DoNormalUpdateActionEv+0x46d6>
  3ce6f8:	e9 1e 04 00 00       	jmp    3ceb1b <_ZN5MCLoc20DoNormalUpdateActionEv+0x46db>
  3ce6fd:	e9 fe 05 00 00       	jmp    3ced00 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c0>
  3ce702:	48 89 c7             	mov    %rax,%rdi
  3ce705:	e8 f6 49 df ff       	call   1c3100 <__clang_call_terminate>
  3ce70a:	48 89 c7             	mov    %rax,%rdi
  3ce70d:	e8 ee 49 df ff       	call   1c3100 <__clang_call_terminate>
  3ce712:	48 89 c7             	mov    %rax,%rdi
  3ce715:	e8 e6 49 df ff       	call   1c3100 <__clang_call_terminate>
  3ce71a:	48 89 c7             	mov    %rax,%rdi
  3ce71d:	e8 de 49 df ff       	call   1c3100 <__clang_call_terminate>
  3ce722:	49 89 c6             	mov    %rax,%r14
  3ce725:	4d 85 ed             	test   %r13,%r13
  3ce728:	0f 84 9c 02 00 00    	je     3ce9ca <_ZN5MCLoc20DoNormalUpdateActionEv+0x458a>
  3ce72e:	48 83 3d fa b3 52 00 	cmpq   $0x0,0x52b3fa(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce735:	00 
  3ce736:	74 15                	je     3ce74d <_ZN5MCLoc20DoNormalUpdateActionEv+0x430d>
  3ce738:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce73d:	f0 41 0f c1 45 08    	lock xadd %eax,0x8(%r13)
  3ce743:	83 f8 01             	cmp    $0x1,%eax
  3ce746:	74 19                	je     3ce761 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4321>
  3ce748:	e9 7d 02 00 00       	jmp    3ce9ca <_ZN5MCLoc20DoNormalUpdateActionEv+0x458a>
  3ce74d:	41 8b 45 08          	mov    0x8(%r13),%eax
  3ce751:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce754:	41 89 4d 08          	mov    %ecx,0x8(%r13)
  3ce758:	83 f8 01             	cmp    $0x1,%eax
  3ce75b:	0f 85 69 02 00 00    	jne    3ce9ca <_ZN5MCLoc20DoNormalUpdateActionEv+0x458a>
  3ce761:	49 8b 45 00          	mov    0x0(%r13),%rax
  3ce765:	4c 89 ef             	mov    %r13,%rdi
  3ce768:	ff 50 10             	call   *0x10(%rax)
  3ce76b:	48 83 3d bd b3 52 00 	cmpq   $0x0,0x52b3bd(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce772:	00 
  3ce773:	74 15                	je     3ce78a <_ZN5MCLoc20DoNormalUpdateActionEv+0x434a>
  3ce775:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce77a:	f0 41 0f c1 45 0c    	lock xadd %eax,0xc(%r13)
  3ce780:	83 f8 01             	cmp    $0x1,%eax
  3ce783:	74 19                	je     3ce79e <_ZN5MCLoc20DoNormalUpdateActionEv+0x435e>
  3ce785:	e9 40 02 00 00       	jmp    3ce9ca <_ZN5MCLoc20DoNormalUpdateActionEv+0x458a>
  3ce78a:	41 8b 45 0c          	mov    0xc(%r13),%eax
  3ce78e:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce791:	41 89 4d 0c          	mov    %ecx,0xc(%r13)
  3ce795:	83 f8 01             	cmp    $0x1,%eax
  3ce798:	0f 85 2c 02 00 00    	jne    3ce9ca <_ZN5MCLoc20DoNormalUpdateActionEv+0x458a>
  3ce79e:	49 8b 45 00          	mov    0x0(%r13),%rax
  3ce7a2:	4c 89 ef             	mov    %r13,%rdi
  3ce7a5:	ff 50 18             	call   *0x18(%rax)
  3ce7a8:	e9 1d 02 00 00       	jmp    3ce9ca <_ZN5MCLoc20DoNormalUpdateActionEv+0x458a>
  3ce7ad:	49 89 c6             	mov    %rax,%r14
  3ce7b0:	e9 1f 02 00 00       	jmp    3ce9d4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4594>
  3ce7b5:	49 89 c6             	mov    %rax,%r14
  3ce7b8:	4c 39 eb             	cmp    %r13,%rbx
  3ce7bb:	0f 84 2c 02 00 00    	je     3ce9ed <_ZN5MCLoc20DoNormalUpdateActionEv+0x45ad>
  3ce7c1:	48 89 df             	mov    %rbx,%rdi
  3ce7c4:	e8 27 11 de ff       	call   1af8f0 <_ZdlPv@plt>
  3ce7c9:	e9 1f 02 00 00       	jmp    3ce9ed <_ZN5MCLoc20DoNormalUpdateActionEv+0x45ad>
  3ce7ce:	49 89 c6             	mov    %rax,%r14
  3ce7d1:	e9 2b 02 00 00       	jmp    3cea01 <_ZN5MCLoc20DoNormalUpdateActionEv+0x45c1>
  3ce7d6:	e9 68 04 00 00       	jmp    3cec43 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4803>
  3ce7db:	e9 20 05 00 00       	jmp    3ced00 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c0>
  3ce7e0:	49 89 c6             	mov    %rax,%r14
  3ce7e3:	4d 85 ed             	test   %r13,%r13
  3ce7e6:	0f 84 da 02 00 00    	je     3ceac6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4686>
  3ce7ec:	48 83 3d 3c b3 52 00 	cmpq   $0x0,0x52b33c(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce7f3:	00 
  3ce7f4:	74 15                	je     3ce80b <_ZN5MCLoc20DoNormalUpdateActionEv+0x43cb>
  3ce7f6:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce7fb:	f0 41 0f c1 45 08    	lock xadd %eax,0x8(%r13)
  3ce801:	83 f8 01             	cmp    $0x1,%eax
  3ce804:	74 19                	je     3ce81f <_ZN5MCLoc20DoNormalUpdateActionEv+0x43df>
  3ce806:	e9 bb 02 00 00       	jmp    3ceac6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4686>
  3ce80b:	41 8b 45 08          	mov    0x8(%r13),%eax
  3ce80f:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce812:	41 89 4d 08          	mov    %ecx,0x8(%r13)
  3ce816:	83 f8 01             	cmp    $0x1,%eax
  3ce819:	0f 85 a7 02 00 00    	jne    3ceac6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4686>
  3ce81f:	49 8b 45 00          	mov    0x0(%r13),%rax
  3ce823:	4c 89 ef             	mov    %r13,%rdi
  3ce826:	ff 50 10             	call   *0x10(%rax)
  3ce829:	48 83 3d ff b2 52 00 	cmpq   $0x0,0x52b2ff(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce830:	00 
  3ce831:	74 15                	je     3ce848 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4408>
  3ce833:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce838:	f0 41 0f c1 45 0c    	lock xadd %eax,0xc(%r13)
  3ce83e:	83 f8 01             	cmp    $0x1,%eax
  3ce841:	74 19                	je     3ce85c <_ZN5MCLoc20DoNormalUpdateActionEv+0x441c>
  3ce843:	e9 7e 02 00 00       	jmp    3ceac6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4686>
  3ce848:	41 8b 45 0c          	mov    0xc(%r13),%eax
  3ce84c:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce84f:	41 89 4d 0c          	mov    %ecx,0xc(%r13)
  3ce853:	83 f8 01             	cmp    $0x1,%eax
  3ce856:	0f 85 6a 02 00 00    	jne    3ceac6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4686>
  3ce85c:	49 8b 45 00          	mov    0x0(%r13),%rax
  3ce860:	4c 89 ef             	mov    %r13,%rdi
  3ce863:	ff 50 18             	call   *0x18(%rax)
  3ce866:	e9 5b 02 00 00       	jmp    3ceac6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4686>
  3ce86b:	49 89 c6             	mov    %rax,%r14
  3ce86e:	e9 61 02 00 00       	jmp    3cead4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4694>
  3ce873:	49 89 c6             	mov    %rax,%r14
  3ce876:	4c 39 eb             	cmp    %r13,%rbx
  3ce879:	0f 84 6e 02 00 00    	je     3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce87f:	48 89 df             	mov    %rbx,%rdi
  3ce882:	e8 69 10 de ff       	call   1af8f0 <_ZdlPv@plt>
  3ce887:	e9 61 02 00 00       	jmp    3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce88c:	49 89 c6             	mov    %rax,%r14
  3ce88f:	e9 6d 02 00 00       	jmp    3ceb01 <_ZN5MCLoc20DoNormalUpdateActionEv+0x46c1>
  3ce894:	49 89 c6             	mov    %rax,%r14
  3ce897:	e9 7f 02 00 00       	jmp    3ceb1b <_ZN5MCLoc20DoNormalUpdateActionEv+0x46db>
  3ce89c:	49 89 c6             	mov    %rax,%r14
  3ce89f:	e9 77 02 00 00       	jmp    3ceb1b <_ZN5MCLoc20DoNormalUpdateActionEv+0x46db>
  3ce8a4:	e9 57 04 00 00       	jmp    3ced00 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c0>
  3ce8a9:	49 89 c6             	mov    %rax,%r14
  3ce8ac:	48 8b 8c 24 b0 00 00 	mov    0xb0(%rsp),%rcx
  3ce8b3:	00 
  3ce8b4:	48 85 c9             	test   %rcx,%rcx
  3ce8b7:	74 12                	je     3ce8cb <_ZN5MCLoc20DoNormalUpdateActionEv+0x448b>
  3ce8b9:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3ce8c0:	00 
  3ce8c1:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce8c6:	48 89 fe             	mov    %rdi,%rsi
  3ce8c9:	ff d1                	call   *%rcx
  3ce8cb:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3ce8d0:	48 85 db             	test   %rbx,%rbx
  3ce8d3:	75 22                	jne    3ce8f7 <_ZN5MCLoc20DoNormalUpdateActionEv+0x44b7>
  3ce8d5:	48 8b 4c 24 68       	mov    0x68(%rsp),%rcx
  3ce8da:	48 85 c9             	test   %rcx,%rcx
  3ce8dd:	0f 84 0a 02 00 00    	je     3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce8e3:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3ce8e8:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce8ed:	48 89 fe             	mov    %rdi,%rsi
  3ce8f0:	ff d1                	call   *%rcx
  3ce8f2:	e9 f6 01 00 00       	jmp    3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ce8f7:	48 83 3d 31 b2 52 00 	cmpq   $0x0,0x52b231(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce8fe:	00 
  3ce8ff:	74 11                	je     3ce912 <_ZN5MCLoc20DoNormalUpdateActionEv+0x44d2>
  3ce901:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce906:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3ce90b:	83 f8 01             	cmp    $0x1,%eax
  3ce90e:	74 10                	je     3ce920 <_ZN5MCLoc20DoNormalUpdateActionEv+0x44e0>
  3ce910:	eb c3                	jmp    3ce8d5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4495>
  3ce912:	8b 43 08             	mov    0x8(%rbx),%eax
  3ce915:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce918:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3ce91b:	83 f8 01             	cmp    $0x1,%eax
  3ce91e:	75 b5                	jne    3ce8d5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4495>
  3ce920:	48 8b 03             	mov    (%rbx),%rax
  3ce923:	48 89 df             	mov    %rbx,%rdi
  3ce926:	ff 50 10             	call   *0x10(%rax)
  3ce929:	48 83 3d ff b1 52 00 	cmpq   $0x0,0x52b1ff(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3ce930:	00 
  3ce931:	74 11                	je     3ce944 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4504>
  3ce933:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3ce938:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3ce93d:	83 f8 01             	cmp    $0x1,%eax
  3ce940:	74 10                	je     3ce952 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4512>
  3ce942:	eb 91                	jmp    3ce8d5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4495>
  3ce944:	8b 43 0c             	mov    0xc(%rbx),%eax
  3ce947:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3ce94a:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3ce94d:	83 f8 01             	cmp    $0x1,%eax
  3ce950:	75 83                	jne    3ce8d5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4495>
  3ce952:	48 8b 03             	mov    (%rbx),%rax
  3ce955:	48 89 df             	mov    %rbx,%rdi
  3ce958:	ff 50 18             	call   *0x18(%rax)
  3ce95b:	e9 75 ff ff ff       	jmp    3ce8d5 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4495>
  3ce960:	48 89 c7             	mov    %rax,%rdi
  3ce963:	e8 98 47 df ff       	call   1c3100 <__clang_call_terminate>
  3ce968:	48 89 c7             	mov    %rax,%rdi
  3ce96b:	e8 90 47 df ff       	call   1c3100 <__clang_call_terminate>
  3ce970:	e9 8b 03 00 00       	jmp    3ced00 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c0>
  3ce975:	e9 86 03 00 00       	jmp    3ced00 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c0>
  3ce97a:	49 89 c6             	mov    %rax,%r14
  3ce97d:	48 8b bc 24 00 03 00 	mov    0x300(%rsp),%rdi
  3ce984:	00 
  3ce985:	48 85 ff             	test   %rdi,%rdi
  3ce988:	0f 84 75 03 00 00    	je     3ced03 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c3>
  3ce98e:	e8 5d 0f de ff       	call   1af8f0 <_ZdlPv@plt>
  3ce993:	e9 6b 03 00 00       	jmp    3ced03 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c3>
  3ce998:	49 89 c6             	mov    %rax,%r14
  3ce99b:	e9 75 03 00 00       	jmp    3ced15 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48d5>
  3ce9a0:	49 89 c6             	mov    %rax,%r14
  3ce9a3:	e9 6d 03 00 00       	jmp    3ced15 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48d5>
  3ce9a8:	49 89 c6             	mov    %rax,%r14
  3ce9ab:	48 8b 8c 24 b0 00 00 	mov    0xb0(%rsp),%rcx
  3ce9b2:	00 
  3ce9b3:	48 85 c9             	test   %rcx,%rcx
  3ce9b6:	74 12                	je     3ce9ca <_ZN5MCLoc20DoNormalUpdateActionEv+0x458a>
  3ce9b8:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3ce9bf:	00 
  3ce9c0:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce9c5:	48 89 fe             	mov    %rdi,%rsi
  3ce9c8:	ff d1                	call   *%rcx
  3ce9ca:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3ce9cf:	48 85 db             	test   %rbx,%rbx
  3ce9d2:	75 50                	jne    3cea24 <_ZN5MCLoc20DoNormalUpdateActionEv+0x45e4>
  3ce9d4:	48 8b 4c 24 68       	mov    0x68(%rsp),%rcx
  3ce9d9:	48 85 c9             	test   %rcx,%rcx
  3ce9dc:	74 0f                	je     3ce9ed <_ZN5MCLoc20DoNormalUpdateActionEv+0x45ad>
  3ce9de:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3ce9e3:	ba 03 00 00 00       	mov    $0x3,%edx
  3ce9e8:	48 89 fe             	mov    %rdi,%rsi
  3ce9eb:	ff d1                	call   *%rcx
  3ce9ed:	48 8b 7c 24 28       	mov    0x28(%rsp),%rdi
  3ce9f2:	48 8d 44 24 38       	lea    0x38(%rsp),%rax
  3ce9f7:	48 39 c7             	cmp    %rax,%rdi
  3ce9fa:	74 05                	je     3cea01 <_ZN5MCLoc20DoNormalUpdateActionEv+0x45c1>
  3ce9fc:	e8 ef 0e de ff       	call   1af8f0 <_ZdlPv@plt>
  3cea01:	48 8b bc 24 c8 00 00 	mov    0xc8(%rsp),%rdi
  3cea08:	00 
  3cea09:	48 8d 84 24 d8 00 00 	lea    0xd8(%rsp),%rax
  3cea10:	00 
  3cea11:	48 39 c7             	cmp    %rax,%rdi
  3cea14:	0f 84 2c 02 00 00    	je     3cec46 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4806>
  3cea1a:	e8 d1 0e de ff       	call   1af8f0 <_ZdlPv@plt>
  3cea1f:	e9 22 02 00 00       	jmp    3cec46 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4806>
  3cea24:	48 83 3d 04 b1 52 00 	cmpq   $0x0,0x52b104(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cea2b:	00 
  3cea2c:	74 11                	je     3cea3f <_ZN5MCLoc20DoNormalUpdateActionEv+0x45ff>
  3cea2e:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cea33:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cea38:	83 f8 01             	cmp    $0x1,%eax
  3cea3b:	74 10                	je     3cea4d <_ZN5MCLoc20DoNormalUpdateActionEv+0x460d>
  3cea3d:	eb 95                	jmp    3ce9d4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4594>
  3cea3f:	8b 43 08             	mov    0x8(%rbx),%eax
  3cea42:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cea45:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cea48:	83 f8 01             	cmp    $0x1,%eax
  3cea4b:	75 87                	jne    3ce9d4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4594>
  3cea4d:	48 8b 03             	mov    (%rbx),%rax
  3cea50:	48 89 df             	mov    %rbx,%rdi
  3cea53:	ff 50 10             	call   *0x10(%rax)
  3cea56:	48 83 3d d2 b0 52 00 	cmpq   $0x0,0x52b0d2(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cea5d:	00 
  3cea5e:	74 14                	je     3cea74 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4634>
  3cea60:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cea65:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cea6a:	83 f8 01             	cmp    $0x1,%eax
  3cea6d:	74 17                	je     3cea86 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4646>
  3cea6f:	e9 60 ff ff ff       	jmp    3ce9d4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4594>
  3cea74:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cea77:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cea7a:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cea7d:	83 f8 01             	cmp    $0x1,%eax
  3cea80:	0f 85 4e ff ff ff    	jne    3ce9d4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4594>
  3cea86:	48 8b 03             	mov    (%rbx),%rax
  3cea89:	48 89 df             	mov    %rbx,%rdi
  3cea8c:	ff 50 18             	call   *0x18(%rax)
  3cea8f:	e9 40 ff ff ff       	jmp    3ce9d4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4594>
  3cea94:	48 89 c7             	mov    %rax,%rdi
  3cea97:	e8 64 46 df ff       	call   1c3100 <__clang_call_terminate>
  3cea9c:	48 89 c7             	mov    %rax,%rdi
  3cea9f:	e8 5c 46 df ff       	call   1c3100 <__clang_call_terminate>
  3ceaa4:	49 89 c6             	mov    %rax,%r14
  3ceaa7:	48 8b 8c 24 b0 00 00 	mov    0xb0(%rsp),%rcx
  3ceaae:	00 
  3ceaaf:	48 85 c9             	test   %rcx,%rcx
  3ceab2:	74 12                	je     3ceac6 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4686>
  3ceab4:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  3ceabb:	00 
  3ceabc:	ba 03 00 00 00       	mov    $0x3,%edx
  3ceac1:	48 89 fe             	mov    %rdi,%rsi
  3ceac4:	ff d1                	call   *%rcx
  3ceac6:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  3ceacb:	48 85 db             	test   %rbx,%rbx
  3ceace:	0f 85 db 00 00 00    	jne    3cebaf <_ZN5MCLoc20DoNormalUpdateActionEv+0x476f>
  3cead4:	48 8b 4c 24 68       	mov    0x68(%rsp),%rcx
  3cead9:	48 85 c9             	test   %rcx,%rcx
  3ceadc:	74 0f                	je     3ceaed <_ZN5MCLoc20DoNormalUpdateActionEv+0x46ad>
  3ceade:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  3ceae3:	ba 03 00 00 00       	mov    $0x3,%edx
  3ceae8:	48 89 fe             	mov    %rdi,%rsi
  3ceaeb:	ff d1                	call   *%rcx
  3ceaed:	48 8b 7c 24 28       	mov    0x28(%rsp),%rdi
  3ceaf2:	48 8d 44 24 38       	lea    0x38(%rsp),%rax
  3ceaf7:	48 39 c7             	cmp    %rax,%rdi
  3ceafa:	74 05                	je     3ceb01 <_ZN5MCLoc20DoNormalUpdateActionEv+0x46c1>
  3ceafc:	e8 ef 0d de ff       	call   1af8f0 <_ZdlPv@plt>
  3ceb01:	48 8b bc 24 c8 00 00 	mov    0xc8(%rsp),%rdi
  3ceb08:	00 
  3ceb09:	48 8d 84 24 d8 00 00 	lea    0xd8(%rsp),%rax
  3ceb10:	00 
  3ceb11:	48 39 c7             	cmp    %rax,%rdi
  3ceb14:	74 05                	je     3ceb1b <_ZN5MCLoc20DoNormalUpdateActionEv+0x46db>
  3ceb16:	e8 d5 0d de ff       	call   1af8f0 <_ZdlPv@plt>
  3ceb1b:	48 8b 1d a6 bf 52 00 	mov    0x52bfa6(%rip),%rbx        # 8faac8 <_ZTTNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3ceb22:	48 8b 03             	mov    (%rbx),%rax
  3ceb25:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3ceb2c:	00 
  3ceb2d:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  3ceb31:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3ceb35:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3ceb3c:	00 
  3ceb3d:	48 8b 43 48          	mov    0x48(%rbx),%rax
  3ceb41:	48 89 84 24 28 01 00 	mov    %rax,0x128(%rsp)
  3ceb48:	00 
  3ceb49:	48 8b 05 a0 87 52 00 	mov    0x5287a0(%rip),%rax        # 8f72f0 <_ZTVNSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3ceb50:	48 83 c0 10          	add    $0x10,%rax
  3ceb54:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3ceb5b:	00 
  3ceb5c:	48 8b bc 24 78 01 00 	mov    0x178(%rsp),%rdi
  3ceb63:	00 
  3ceb64:	48 8d 84 24 88 01 00 	lea    0x188(%rsp),%rax
  3ceb6b:	00 
  3ceb6c:	48 39 c7             	cmp    %rax,%rdi
  3ceb6f:	74 05                	je     3ceb76 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4736>
  3ceb71:	e8 7a 0d de ff       	call   1af8f0 <_ZdlPv@plt>
  3ceb76:	48 8b 05 d3 9e 52 00 	mov    0x529ed3(%rip),%rax        # 8f8a50 <_ZTVSt15basic_streambufIcSt11char_traitsIcEE@GLIBCXX_3.4>
  3ceb7d:	48 83 c0 10          	add    $0x10,%rax
  3ceb81:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3ceb88:	00 
  3ceb89:	48 8d bc 24 68 01 00 	lea    0x168(%rsp),%rdi
  3ceb90:	00 
  3ceb91:	e8 6a 4f de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3ceb96:	48 8b 43 10          	mov    0x10(%rbx),%rax
  3ceb9a:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  3ceb9e:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3ceba5:	00 
  3ceba6:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cebaa:	e9 2e 01 00 00       	jmp    3cecdd <_ZN5MCLoc20DoNormalUpdateActionEv+0x489d>
  3cebaf:	48 83 3d 79 af 52 00 	cmpq   $0x0,0x52af79(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cebb6:	00 
  3cebb7:	74 14                	je     3cebcd <_ZN5MCLoc20DoNormalUpdateActionEv+0x478d>
  3cebb9:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cebbe:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
  3cebc3:	83 f8 01             	cmp    $0x1,%eax
  3cebc6:	74 17                	je     3cebdf <_ZN5MCLoc20DoNormalUpdateActionEv+0x479f>
  3cebc8:	e9 07 ff ff ff       	jmp    3cead4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4694>
  3cebcd:	8b 43 08             	mov    0x8(%rbx),%eax
  3cebd0:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cebd3:	89 4b 08             	mov    %ecx,0x8(%rbx)
  3cebd6:	83 f8 01             	cmp    $0x1,%eax
  3cebd9:	0f 85 f5 fe ff ff    	jne    3cead4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4694>
  3cebdf:	48 8b 03             	mov    (%rbx),%rax
  3cebe2:	48 89 df             	mov    %rbx,%rdi
  3cebe5:	ff 50 10             	call   *0x10(%rax)
  3cebe8:	48 83 3d 40 af 52 00 	cmpq   $0x0,0x52af40(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cebef:	00 
  3cebf0:	74 14                	je     3cec06 <_ZN5MCLoc20DoNormalUpdateActionEv+0x47c6>
  3cebf2:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cebf7:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
  3cebfc:	83 f8 01             	cmp    $0x1,%eax
  3cebff:	74 17                	je     3cec18 <_ZN5MCLoc20DoNormalUpdateActionEv+0x47d8>
  3cec01:	e9 ce fe ff ff       	jmp    3cead4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4694>
  3cec06:	8b 43 0c             	mov    0xc(%rbx),%eax
  3cec09:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cec0c:	89 4b 0c             	mov    %ecx,0xc(%rbx)
  3cec0f:	83 f8 01             	cmp    $0x1,%eax
  3cec12:	0f 85 bc fe ff ff    	jne    3cead4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4694>
  3cec18:	48 8b 03             	mov    (%rbx),%rax
  3cec1b:	48 89 df             	mov    %rbx,%rdi
  3cec1e:	ff 50 18             	call   *0x18(%rax)
  3cec21:	e9 ae fe ff ff       	jmp    3cead4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4694>
  3cec26:	48 89 c7             	mov    %rax,%rdi
  3cec29:	e8 d2 44 df ff       	call   1c3100 <__clang_call_terminate>
  3cec2e:	48 89 c7             	mov    %rax,%rdi
  3cec31:	e8 ca 44 df ff       	call   1c3100 <__clang_call_terminate>
  3cec36:	e9 c5 00 00 00       	jmp    3ced00 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c0>
  3cec3b:	49 89 c6             	mov    %rax,%r14
  3cec3e:	e9 d2 00 00 00       	jmp    3ced15 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48d5>
  3cec43:	49 89 c6             	mov    %rax,%r14
  3cec46:	48 8b 84 24 00 01 00 	mov    0x100(%rsp),%rax
  3cec4d:	00 
  3cec4e:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cec55:	00 
  3cec56:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cec5a:	48 8b 8c 24 f0 00 00 	mov    0xf0(%rsp),%rcx
  3cec61:	00 
  3cec62:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cec69:	00 
  3cec6a:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  3cec71:	00 
  3cec72:	48 89 84 24 28 01 00 	mov    %rax,0x128(%rsp)
  3cec79:	00 
  3cec7a:	48 8b 84 24 10 01 00 	mov    0x110(%rsp),%rax
  3cec81:	00 
  3cec82:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cec89:	00 
  3cec8a:	48 8b bc 24 78 01 00 	mov    0x178(%rsp),%rdi
  3cec91:	00 
  3cec92:	48 8d 84 24 88 01 00 	lea    0x188(%rsp),%rax
  3cec99:	00 
  3cec9a:	48 39 c7             	cmp    %rax,%rdi
  3cec9d:	74 05                	je     3ceca4 <_ZN5MCLoc20DoNormalUpdateActionEv+0x4864>
  3cec9f:	e8 4c 0c de ff       	call   1af8f0 <_ZdlPv@plt>
  3ceca4:	48 8b 84 24 f0 02 00 	mov    0x2f0(%rsp),%rax
  3cecab:	00 
  3cecac:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  3cecb3:	00 
  3cecb4:	48 8d bc 24 68 01 00 	lea    0x168(%rsp),%rdi
  3cecbb:	00 
  3cecbc:	e8 3f 4e de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3cecc1:	48 8b 84 24 e0 02 00 	mov    0x2e0(%rsp),%rax
  3cecc8:	00 
  3cecc9:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  3cecd0:	00 
  3cecd1:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cecd5:	48 8b 8c 24 e8 02 00 	mov    0x2e8(%rsp),%rcx
  3cecdc:	00 
  3cecdd:	48 89 8c 04 18 01 00 	mov    %rcx,0x118(%rsp,%rax,1)
  3cece4:	00 
  3cece5:	48 c7 84 24 20 01 00 	movq   $0x0,0x120(%rsp)
  3cecec:	00 00 00 00 00 
  3cecf1:	48 8d bc 24 98 01 00 	lea    0x198(%rsp),%rdi
  3cecf8:	00 
  3cecf9:	e8 c2 99 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3cecfe:	eb 03                	jmp    3ced03 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48c3>
  3ced00:	49 89 c6             	mov    %rax,%r14
  3ced03:	48 8b bc 24 a0 02 00 	mov    0x2a0(%rsp),%rdi
  3ced0a:	00 
  3ced0b:	48 85 ff             	test   %rdi,%rdi
  3ced0e:	74 05                	je     3ced15 <_ZN5MCLoc20DoNormalUpdateActionEv+0x48d5>
  3ced10:	e8 db 0b de ff       	call   1af8f0 <_ZdlPv@plt>
  3ced15:	48 8d bc 24 f8 02 00 	lea    0x2f8(%rsp),%rdi
  3ced1c:	00 
  3ced1d:	e8 6e 1d de ff       	call   1b0a90 <_ZN8profiler10ScopedZoneD1Ev@plt>
  3ced22:	4c 89 f7             	mov    %r14,%rdi
  3ced25:	e8 66 6b de ff       	call   1b5890 <_Unwind_Resume@plt>
  3ced2a:	66 0f 1f 44 00 00    	nopw   0x0(%rax,%rax,1)

00000000003ced30 <_ZN5MCLoc11RelocWithPFEv>:
  3ced30:	55                   	push   %rbp
  3ced31:	48 89 e5             	mov    %rsp,%rbp
  3ced34:	41 57                	push   %r15
  3ced36:	41 56                	push   %r14
  3ced38:	41 55                	push   %r13
  3ced3a:	41 54                	push   %r12
  3ced3c:	53                   	push   %rbx
  3ced3d:	48 83 e4 f0          	and    $0xfffffffffffffff0,%rsp
  3ced41:	48 81 ec d0 03 00 00 	sub    $0x3d0,%rsp
  3ced48:	49 89 fe             	mov    %rdi,%r14
  3ced4b:	31 c0                	xor    %eax,%eax
  3ced4d:	31 c9                	xor    %ecx,%ecx
  3ced4f:	41 86 8e c0 e4 d0 03 	xchg   %cl,0x3d0e4c0(%r14)
  3ced56:	41 8a 8e f8 cf d0 03 	mov    0x3d0cff8(%r14),%cl
  3ced5d:	80 e1 01             	and    $0x1,%cl
  3ced60:	41 86 86 90 cf d0 03 	xchg   %al,0x3d0cf90(%r14)
  3ced67:	41 88 8e 8d d1 d0 03 	mov    %cl,0x3d0d18d(%r14)
  3ced6e:	e8 0d 96 de ff       	call   1b8380 <_ZN5MCLoc13DoRelocActionERN3rbk9algorithm10StateVar2DE@plt>
  3ced73:	4c 89 f7             	mov    %r14,%rdi
  3ced76:	e8 55 3f de ff       	call   1b2cd0 <_ZN5MCLoc18DoLaserDataProcessEv@plt>
  3ced7b:	41 89 c7             	mov    %eax,%r15d
  3ced7e:	49 8d 9e 30 11 00 00 	lea    0x1130(%r14),%rbx
  3ced85:	48 89 df             	mov    %rbx,%rdi
  3ced88:	e8 43 98 de ff       	call   1b85d0 <_ZN5boost5mutex4lockEv@plt>
  3ced8d:	e8 7e 62 de ff       	call   1b5010 <_ZN3rbk10ErrorCodes8InstanceEv@plt>
  3ced92:	be 8d cb 00 00       	mov    $0xcb8d,%esi
  3ced97:	48 89 c7             	mov    %rax,%rdi
  3ced9a:	e8 11 0f de ff       	call   1afcb0 <_ZN3rbk10ErrorCodes11errorExistsEt@plt>
  3ced9f:	84 c0                	test   %al,%al
  3ceda1:	74 60                	je     3cee03 <_ZN5MCLoc11RelocWithPFEv+0xd3>
  3ceda3:	e8 68 62 de ff       	call   1b5010 <_ZN3rbk10ErrorCodes8InstanceEv@plt>
  3ceda8:	be 8d cb 00 00       	mov    $0xcb8d,%esi
  3cedad:	48 89 c7             	mov    %rax,%rdi
  3cedb0:	e8 db 0c de ff       	call   1afa90 <_ZN3rbk10ErrorCodes10clearErrorEt@plt>
  3cedb5:	49 8b 8e f0 10 00 00 	mov    0x10f0(%r14),%rcx
  3cedbc:	49 8b 86 f8 10 00 00 	mov    0x10f8(%r14),%rax
  3cedc3:	48 29 c8             	sub    %rcx,%rax
  3cedc6:	74 3b                	je     3cee03 <_ZN5MCLoc11RelocWithPFEv+0xd3>
  3cedc8:	48 c1 f8 04          	sar    $0x4,%rax
  3cedcc:	48 ba c5 4e ec c4 4e 	movabs $0x4ec4ec4ec4ec4ec5,%rdx
  3cedd3:	ec c4 4e 
  3cedd6:	48 0f af d0          	imul   %rax,%rdx
  3cedda:	48 81 c1 a4 00 00 00 	add    $0xa4,%rcx
  3cede1:	31 c0                	xor    %eax,%eax
  3cede3:	66 66 66 66 2e 0f 1f 	data16 data16 data16 cs nopw 0x0(%rax,%rax,1)
  3cedea:	84 00 00 00 00 00 
  3cedf0:	c6 01 00             	movb   $0x0,(%rcx)
  3cedf3:	48 83 c0 01          	add    $0x1,%rax
  3cedf7:	48 81 c1 d0 00 00 00 	add    $0xd0,%rcx
  3cedfe:	48 39 c2             	cmp    %rax,%rdx
  3cee01:	77 ed                	ja     3cedf0 <_ZN5MCLoc11RelocWithPFEv+0xc0>
  3cee03:	45 84 ff             	test   %r15b,%r15b
  3cee06:	4c 89 b4 24 e8 00 00 	mov    %r14,0xe8(%rsp)
  3cee0d:	00 
  3cee0e:	0f 84 16 01 00 00    	je     3cef2a <_ZN5MCLoc11RelocWithPFEv+0x1fa>
  3cee14:	4c 8d bc 24 50 01 00 	lea    0x150(%rsp),%r15
  3cee1b:	00 
  3cee1c:	4c 89 bc 24 40 01 00 	mov    %r15,0x140(%rsp)
  3cee23:	00 
  3cee24:	48 b8 72 65 6c 6f 63 	movabs $0x696146636f6c6572,%rax
  3cee2b:	46 61 69 
  3cee2e:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3cee35:	00 
  3cee36:	c7 84 24 58 01 00 00 	movl   $0x64656c,0x158(%rsp)
  3cee3d:	6c 65 64 00 
  3cee41:	48 c7 84 24 48 01 00 	movq   $0xb,0x148(%rsp)
  3cee48:	00 0b 00 00 00 
  3cee4d:	48 8d b4 24 40 01 00 	lea    0x140(%rsp),%rsi
  3cee54:	00 
  3cee55:	4c 89 f7             	mov    %r14,%rdi
  3cee58:	e8 a3 a1 de ff       	call   1b9000 <_ZN5MCLoc9FireEventERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE@plt>
  3cee5d:	48 8b bc 24 40 01 00 	mov    0x140(%rsp),%rdi
  3cee64:	00 
  3cee65:	4c 39 ff             	cmp    %r15,%rdi
  3cee68:	74 05                	je     3cee6f <_ZN5MCLoc11RelocWithPFEv+0x13f>
  3cee6a:	e8 81 0a de ff       	call   1af8f0 <_ZdlPv@plt>
  3cee6f:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  3cee76:	00 
  3cee77:	be 18 00 00 00       	mov    $0x18,%esi
  3cee7c:	e8 8f 5f de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3cee81:	48 8d bc 24 50 01 00 	lea    0x150(%rsp),%rdi
  3cee88:	00 
  3cee89:	48 8d 35 06 1f 1a 00 	lea    0x1a1f06(%rip),%rsi        # 570d96 <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc9FireEventERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEE4$_80JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x33f6>
  3cee90:	ba 0b 00 00 00       	mov    $0xb,%edx
  3cee95:	e8 56 1c de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3cee9a:	48 8d b4 24 58 01 00 	lea    0x158(%rsp),%rsi
  3ceea1:	00 
  3ceea2:	48 8d bc 24 90 00 00 	lea    0x90(%rsp),%rdi
  3ceea9:	00 
  3ceeaa:	e8 b1 5d de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3ceeaf:	e8 2c 8a de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3ceeb4:	49 89 c4             	mov    %rax,%r12
  3ceeb7:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3ceebc:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3ceec1:	4c 8b bc 24 90 00 00 	mov    0x90(%rsp),%r15
  3ceec8:	00 
  3ceec9:	4c 8b ac 24 98 00 00 	mov    0x98(%rsp),%r13
  3ceed0:	00 
  3ceed1:	4d 85 ff             	test   %r15,%r15
  3ceed4:	75 09                	jne    3ceedf <_ZN5MCLoc11RelocWithPFEv+0x1af>
  3ceed6:	4d 85 ed             	test   %r13,%r13
  3ceed9:	0f 85 02 2d 00 00    	jne    3d1be1 <_ZN5MCLoc11RelocWithPFEv+0x2eb1>
  3ceedf:	49 89 ce             	mov    %rcx,%r14
  3ceee2:	49 83 fd 10          	cmp    $0x10,%r13
  3ceee6:	72 24                	jb     3cef0c <_ZN5MCLoc11RelocWithPFEv+0x1dc>
  3ceee8:	4d 85 ed             	test   %r13,%r13
  3ceeeb:	0f 88 20 2d 00 00    	js     3d1c11 <_ZN5MCLoc11RelocWithPFEv+0x2ee1>
  3ceef1:	49 8d 7d 01          	lea    0x1(%r13),%rdi
  3ceef5:	e8 66 83 de ff       	call   1b7260 <_Znwm@plt>
  3ceefa:	49 89 c6             	mov    %rax,%r14
  3ceefd:	4c 89 74 24 08       	mov    %r14,0x8(%rsp)
  3cef02:	4c 89 6c 24 18       	mov    %r13,0x18(%rsp)
  3cef07:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3cef0c:	4d 85 ed             	test   %r13,%r13
  3cef0f:	0f 84 d3 01 00 00    	je     3cf0e8 <_ZN5MCLoc11RelocWithPFEv+0x3b8>
  3cef15:	49 83 fd 01          	cmp    $0x1,%r13
  3cef19:	0f 85 b6 01 00 00    	jne    3cf0d5 <_ZN5MCLoc11RelocWithPFEv+0x3a5>
  3cef1f:	41 8a 07             	mov    (%r15),%al
  3cef22:	41 88 06             	mov    %al,(%r14)
  3cef25:	e9 be 01 00 00       	jmp    3cf0e8 <_ZN5MCLoc11RelocWithPFEv+0x3b8>
  3cef2a:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  3cef31:	00 
  3cef32:	be 18 00 00 00       	mov    $0x18,%esi
  3cef37:	e8 d4 5e de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3cef3c:	4c 8d 7c 24 78       	lea    0x78(%rsp),%r15
  3cef41:	4c 89 7c 24 68       	mov    %r15,0x68(%rsp)
  3cef46:	0f 28 05 63 08 1f 00 	movaps 0x1f0863(%rip),%xmm0        # 5bf7b0 <_ZTSZN3rbk6Logger6Thread11move2threadIZN4seer20ParticleFilterOpenCL10SetProgramERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEE4$_29JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x2b0>
  3cef4d:	0f 11 44 24 70       	movups %xmm0,0x70(%rsp)
  3cef52:	c6 84 24 80 00 00 00 	movb   $0x0,0x80(%rsp)
  3cef59:	00 
  3cef5a:	f2 41 0f 10 86 60 0f 	movsd  0xf60(%r14),%xmm0
  3cef61:	00 00 
  3cef63:	f2 0f 59 05 0d 3a 19 	mulsd  0x193a0d(%rip),%xmm0        # 562978 <_ZTS11errorLogger+0x2e>
  3cef6a:	00 
  3cef6b:	4d 8d a6 50 0f 00 00 	lea    0xf50(%r14),%r12
  3cef72:	48 8b 05 bf b1 52 00 	mov    0x52b1bf(%rip),%rax        # 8fa138 <_ZN3rbk10foundation4math2PIE>
  3cef79:	f2 0f 5e 00          	divsd  (%rax),%xmm0
  3cef7d:	49 8d 8e 58 0f 00 00 	lea    0xf58(%r14),%rcx
  3cef84:	f2 0f 11 44 24 28    	movsd  %xmm0,0x28(%rsp)
  3cef8a:	4d 8d 8e 60 d0 d0 03 	lea    0x3d0d060(%r14),%r9
  3cef91:	c7 84 24 90 00 00 00 	movl   $0x0,0x90(%rsp)
  3cef98:	00 00 00 00 
  3cef9c:	c7 44 24 08 00 00 00 	movl   $0x0,0x8(%rsp)
  3cefa3:	00 
  3cefa4:	c7 44 24 48 00 00 00 	movl   $0x0,0x48(%rsp)
  3cefab:	00 
  3cefac:	c7 84 24 f0 02 00 00 	movl   $0x0,0x2f0(%rsp)
  3cefb3:	00 00 00 00 
  3cefb7:	48 8d 84 24 f0 02 00 	lea    0x2f0(%rsp),%rax
  3cefbe:	00 
  3cefbf:	4c 8d 54 24 48       	lea    0x48(%rsp),%r10
  3cefc4:	4c 8d 5c 24 08       	lea    0x8(%rsp),%r11
  3cefc9:	4c 8d b4 24 90 00 00 	lea    0x90(%rsp),%r14
  3cefd0:	00 
  3cefd1:	48 8d bc 24 f0 00 00 	lea    0xf0(%rsp),%rdi
  3cefd8:	00 
  3cefd9:	48 8d 74 24 68       	lea    0x68(%rsp),%rsi
  3cefde:	4c 8d 44 24 28       	lea    0x28(%rsp),%r8
  3cefe3:	4c 89 e2             	mov    %r12,%rdx
  3cefe6:	50                   	push   %rax
  3cefe7:	41 52                	push   %r10
  3cefe9:	41 53                	push   %r11
  3cefeb:	41 56                	push   %r14
  3cefed:	e8 ce 3e de ff       	call   1b2ec0 <_Z9formatLogIJddddiiiiEENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEERKS5_DpRKT_@plt>
  3ceff2:	48 83 c4 20          	add    $0x20,%rsp
  3ceff6:	48 8d bc 24 50 01 00 	lea    0x150(%rsp),%rdi
  3ceffd:	00 
  3ceffe:	48 8b b4 24 f0 00 00 	mov    0xf0(%rsp),%rsi
  3cf005:	00 
  3cf006:	48 8b 94 24 f8 00 00 	mov    0xf8(%rsp),%rdx
  3cf00d:	00 
  3cf00e:	e8 dd 1a de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3cf013:	48 8b bc 24 f0 00 00 	mov    0xf0(%rsp),%rdi
  3cf01a:	00 
  3cf01b:	48 8d 84 24 00 01 00 	lea    0x100(%rsp),%rax
  3cf022:	00 
  3cf023:	48 39 c7             	cmp    %rax,%rdi
  3cf026:	74 05                	je     3cf02d <_ZN5MCLoc11RelocWithPFEv+0x2fd>
  3cf028:	e8 c3 08 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cf02d:	48 8b 7c 24 68       	mov    0x68(%rsp),%rdi
  3cf032:	4c 39 ff             	cmp    %r15,%rdi
  3cf035:	74 05                	je     3cf03c <_ZN5MCLoc11RelocWithPFEv+0x30c>
  3cf037:	e8 b4 08 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cf03c:	48 8d b4 24 58 01 00 	lea    0x158(%rsp),%rsi
  3cf043:	00 
  3cf044:	48 8d bc 24 90 00 00 	lea    0x90(%rsp),%rdi
  3cf04b:	00 
  3cf04c:	e8 0f 5c de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3cf051:	4c 89 a4 24 e0 02 00 	mov    %r12,0x2e0(%rsp)
  3cf058:	00 
  3cf059:	e8 82 88 de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3cf05e:	49 89 c5             	mov    %rax,%r13
  3cf061:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3cf066:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3cf06b:	4c 8b a4 24 90 00 00 	mov    0x90(%rsp),%r12
  3cf072:	00 
  3cf073:	4c 8b bc 24 98 00 00 	mov    0x98(%rsp),%r15
  3cf07a:	00 
  3cf07b:	4d 85 e4             	test   %r12,%r12
  3cf07e:	75 09                	jne    3cf089 <_ZN5MCLoc11RelocWithPFEv+0x359>
  3cf080:	4d 85 ff             	test   %r15,%r15
  3cf083:	0f 85 64 2b 00 00    	jne    3d1bed <_ZN5MCLoc11RelocWithPFEv+0x2ebd>
  3cf089:	49 89 ce             	mov    %rcx,%r14
  3cf08c:	49 83 ff 10          	cmp    $0x10,%r15
  3cf090:	72 24                	jb     3cf0b6 <_ZN5MCLoc11RelocWithPFEv+0x386>
  3cf092:	4d 85 ff             	test   %r15,%r15
  3cf095:	0f 88 82 2b 00 00    	js     3d1c1d <_ZN5MCLoc11RelocWithPFEv+0x2eed>
  3cf09b:	49 8d 7f 01          	lea    0x1(%r15),%rdi
  3cf09f:	e8 bc 81 de ff       	call   1b7260 <_Znwm@plt>
  3cf0a4:	49 89 c6             	mov    %rax,%r14
  3cf0a7:	4c 89 74 24 08       	mov    %r14,0x8(%rsp)
  3cf0ac:	4c 89 7c 24 18       	mov    %r15,0x18(%rsp)
  3cf0b1:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3cf0b6:	4d 85 ff             	test   %r15,%r15
  3cf0b9:	0f 84 8e 01 00 00    	je     3cf24d <_ZN5MCLoc11RelocWithPFEv+0x51d>
  3cf0bf:	49 83 ff 01          	cmp    $0x1,%r15
  3cf0c3:	0f 85 71 01 00 00    	jne    3cf23a <_ZN5MCLoc11RelocWithPFEv+0x50a>
  3cf0c9:	41 8a 04 24          	mov    (%r12),%al
  3cf0cd:	41 88 06             	mov    %al,(%r14)
  3cf0d0:	e9 78 01 00 00       	jmp    3cf24d <_ZN5MCLoc11RelocWithPFEv+0x51d>
  3cf0d5:	4c 89 f7             	mov    %r14,%rdi
  3cf0d8:	4c 89 fe             	mov    %r15,%rsi
  3cf0db:	4c 89 ea             	mov    %r13,%rdx
  3cf0de:	e8 9d 7e de ff       	call   1b6f80 <memcpy@plt>
  3cf0e3:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3cf0e8:	4c 89 6c 24 10       	mov    %r13,0x10(%rsp)
  3cf0ed:	43 c6 04 2e 00       	movb   $0x0,(%r14,%r13,1)
  3cf0f2:	4c 8d ac 24 00 01 00 	lea    0x100(%rsp),%r13
  3cf0f9:	00 
  3cf0fa:	4c 89 ac 24 f0 00 00 	mov    %r13,0xf0(%rsp)
  3cf101:	00 
  3cf102:	4c 8b 7c 24 08       	mov    0x8(%rsp),%r15
  3cf107:	49 39 cf             	cmp    %rcx,%r15
  3cf10a:	74 17                	je     3cf123 <_ZN5MCLoc11RelocWithPFEv+0x3f3>
  3cf10c:	4c 89 bc 24 f0 00 00 	mov    %r15,0xf0(%rsp)
  3cf113:	00 
  3cf114:	48 8b 44 24 18       	mov    0x18(%rsp),%rax
  3cf119:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  3cf120:	00 
  3cf121:	eb 0d                	jmp    3cf130 <_ZN5MCLoc11RelocWithPFEv+0x400>
  3cf123:	66 0f 10 01          	movupd (%rcx),%xmm0
  3cf127:	66 41 0f 11 45 00    	movupd %xmm0,0x0(%r13)
  3cf12d:	4d 89 ef             	mov    %r13,%r15
  3cf130:	4c 8b 74 24 10       	mov    0x10(%rsp),%r14
  3cf135:	4c 89 b4 24 f8 00 00 	mov    %r14,0xf8(%rsp)
  3cf13c:	00 
  3cf13d:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3cf142:	48 c7 44 24 10 00 00 	movq   $0x0,0x10(%rsp)
  3cf149:	00 00 
  3cf14b:	c6 44 24 18 00       	movb   $0x0,0x18(%rsp)
  3cf150:	48 c7 44 24 78 00 00 	movq   $0x0,0x78(%rsp)
  3cf157:	00 00 
  3cf159:	bf 28 00 00 00       	mov    $0x28,%edi
  3cf15e:	e8 fd 80 de ff       	call   1b7260 <_Znwm@plt>
  3cf163:	48 89 c1             	mov    %rax,%rcx
  3cf166:	48 83 c1 10          	add    $0x10,%rcx
  3cf16a:	48 89 08             	mov    %rcx,(%rax)
  3cf16d:	4d 39 ef             	cmp    %r13,%r15
  3cf170:	74 11                	je     3cf183 <_ZN5MCLoc11RelocWithPFEv+0x453>
  3cf172:	4c 89 38             	mov    %r15,(%rax)
  3cf175:	48 8b 8c 24 00 01 00 	mov    0x100(%rsp),%rcx
  3cf17c:	00 
  3cf17d:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3cf181:	eb 0a                	jmp    3cf18d <_ZN5MCLoc11RelocWithPFEv+0x45d>
  3cf183:	66 41 0f 10 45 00    	movupd 0x0(%r13),%xmm0
  3cf189:	66 0f 11 01          	movupd %xmm0,(%rcx)
  3cf18d:	4c 89 ac 24 f0 00 00 	mov    %r13,0xf0(%rsp)
  3cf194:	00 
  3cf195:	48 c7 84 24 f8 00 00 	movq   $0x0,0xf8(%rsp)
  3cf19c:	00 00 00 00 00 
  3cf1a1:	c6 84 24 00 01 00 00 	movb   $0x0,0x100(%rsp)
  3cf1a8:	00 
  3cf1a9:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3cf1ad:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cf1b2:	48 8d 05 b7 2b 01 00 	lea    0x12bb7(%rip),%rax        # 3e1d70 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc11RelocWithPFEvE4$_15vEEE9_M_invokeERKSt9_Any_data>
  3cf1b9:	48 89 84 24 80 00 00 	mov    %rax,0x80(%rsp)
  3cf1c0:	00 
  3cf1c1:	48 8d 05 88 2d 01 00 	lea    0x12d88(%rip),%rax        # 3e1f50 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc11RelocWithPFEvE4$_15vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3cf1c8:	48 89 44 24 78       	mov    %rax,0x78(%rsp)
  3cf1cd:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3cf1d4:	00 00 
  3cf1d6:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3cf1db:	48 8d 54 24 28       	lea    0x28(%rsp),%rdx
  3cf1e0:	48 8d 4c 24 68       	lea    0x68(%rsp),%rcx
  3cf1e5:	31 f6                	xor    %esi,%esi
  3cf1e7:	e8 a4 4a de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3cf1ec:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3cf1f1:	48 85 ff             	test   %rdi,%rdi
  3cf1f4:	74 17                	je     3cf20d <_ZN5MCLoc11RelocWithPFEv+0x4dd>
  3cf1f6:	48 8b 07             	mov    (%rdi),%rax
  3cf1f9:	48 8b 35 d0 a7 52 00 	mov    0x52a7d0(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3cf200:	ff 50 20             	call   *0x20(%rax)
  3cf203:	49 89 c7             	mov    %rax,%r15
  3cf206:	4c 8b 6c 24 50       	mov    0x50(%rsp),%r13
  3cf20b:	eb 06                	jmp    3cf213 <_ZN5MCLoc11RelocWithPFEv+0x4e3>
  3cf20d:	45 31 ed             	xor    %r13d,%r13d
  3cf210:	45 31 ff             	xor    %r15d,%r15d
  3cf213:	4c 89 7c 24 48       	mov    %r15,0x48(%rsp)
  3cf218:	4d 85 ed             	test   %r13,%r13
  3cf21b:	0f 84 87 01 00 00    	je     3cf3a8 <_ZN5MCLoc11RelocWithPFEv+0x678>
  3cf221:	48 83 3d 07 a9 52 00 	cmpq   $0x0,0x52a907(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cf228:	00 
  3cf229:	0f 84 74 01 00 00    	je     3cf3a3 <_ZN5MCLoc11RelocWithPFEv+0x673>
  3cf22f:	f0 41 83 45 08 01    	lock addl $0x1,0x8(%r13)
  3cf235:	e9 6e 01 00 00       	jmp    3cf3a8 <_ZN5MCLoc11RelocWithPFEv+0x678>
  3cf23a:	4c 89 f7             	mov    %r14,%rdi
  3cf23d:	4c 89 e6             	mov    %r12,%rsi
  3cf240:	4c 89 fa             	mov    %r15,%rdx
  3cf243:	e8 38 7d de ff       	call   1b6f80 <memcpy@plt>
  3cf248:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3cf24d:	4c 89 7c 24 10       	mov    %r15,0x10(%rsp)
  3cf252:	43 c6 04 3e 00       	movb   $0x0,(%r14,%r15,1)
  3cf257:	48 8d 84 24 00 01 00 	lea    0x100(%rsp),%rax
  3cf25e:	00 
  3cf25f:	48 89 84 24 f0 00 00 	mov    %rax,0xf0(%rsp)
  3cf266:	00 
  3cf267:	4c 8b 7c 24 08       	mov    0x8(%rsp),%r15
  3cf26c:	49 39 cf             	cmp    %rcx,%r15
  3cf26f:	74 17                	je     3cf288 <_ZN5MCLoc11RelocWithPFEv+0x558>
  3cf271:	4c 89 bc 24 f0 00 00 	mov    %r15,0xf0(%rsp)
  3cf278:	00 
  3cf279:	48 8b 44 24 18       	mov    0x18(%rsp),%rax
  3cf27e:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  3cf285:	00 
  3cf286:	eb 0b                	jmp    3cf293 <_ZN5MCLoc11RelocWithPFEv+0x563>
  3cf288:	66 0f 10 01          	movupd (%rcx),%xmm0
  3cf28c:	66 0f 11 00          	movupd %xmm0,(%rax)
  3cf290:	49 89 c7             	mov    %rax,%r15
  3cf293:	4c 8b 74 24 10       	mov    0x10(%rsp),%r14
  3cf298:	4c 89 b4 24 f8 00 00 	mov    %r14,0xf8(%rsp)
  3cf29f:	00 
  3cf2a0:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3cf2a5:	48 c7 44 24 10 00 00 	movq   $0x0,0x10(%rsp)
  3cf2ac:	00 00 
  3cf2ae:	c6 44 24 18 00       	movb   $0x0,0x18(%rsp)
  3cf2b3:	48 c7 44 24 78 00 00 	movq   $0x0,0x78(%rsp)
  3cf2ba:	00 00 
  3cf2bc:	bf 28 00 00 00       	mov    $0x28,%edi
  3cf2c1:	e8 9a 7f de ff       	call   1b7260 <_Znwm@plt>
  3cf2c6:	48 89 c1             	mov    %rax,%rcx
  3cf2c9:	48 83 c1 10          	add    $0x10,%rcx
  3cf2cd:	48 89 08             	mov    %rcx,(%rax)
  3cf2d0:	48 8d 94 24 00 01 00 	lea    0x100(%rsp),%rdx
  3cf2d7:	00 
  3cf2d8:	49 39 d7             	cmp    %rdx,%r15
  3cf2db:	74 11                	je     3cf2ee <_ZN5MCLoc11RelocWithPFEv+0x5be>
  3cf2dd:	4c 89 38             	mov    %r15,(%rax)
  3cf2e0:	48 8b 8c 24 00 01 00 	mov    0x100(%rsp),%rcx
  3cf2e7:	00 
  3cf2e8:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3cf2ec:	eb 08                	jmp    3cf2f6 <_ZN5MCLoc11RelocWithPFEv+0x5c6>
  3cf2ee:	66 0f 10 02          	movupd (%rdx),%xmm0
  3cf2f2:	66 0f 11 01          	movupd %xmm0,(%rcx)
  3cf2f6:	48 89 94 24 f0 00 00 	mov    %rdx,0xf0(%rsp)
  3cf2fd:	00 
  3cf2fe:	48 c7 84 24 f8 00 00 	movq   $0x0,0xf8(%rsp)
  3cf305:	00 00 00 00 00 
  3cf30a:	c6 84 24 00 01 00 00 	movb   $0x0,0x100(%rsp)
  3cf311:	00 
  3cf312:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3cf316:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cf31b:	48 8d 05 0e 10 01 00 	lea    0x1100e(%rip),%rax        # 3e0330 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc11RelocWithPFEvE3$_9vEEE9_M_invokeERKSt9_Any_data>
  3cf322:	48 89 84 24 80 00 00 	mov    %rax,0x80(%rsp)
  3cf329:	00 
  3cf32a:	48 8d 05 df 11 01 00 	lea    0x111df(%rip),%rax        # 3e0510 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc11RelocWithPFEvE3$_9vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3cf331:	48 89 44 24 78       	mov    %rax,0x78(%rsp)
  3cf336:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3cf33d:	00 00 
  3cf33f:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3cf344:	48 8d 54 24 28       	lea    0x28(%rsp),%rdx
  3cf349:	48 8d 4c 24 68       	lea    0x68(%rsp),%rcx
  3cf34e:	31 f6                	xor    %esi,%esi
  3cf350:	e8 3b 49 de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3cf355:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3cf35a:	48 85 ff             	test   %rdi,%rdi
  3cf35d:	74 17                	je     3cf376 <_ZN5MCLoc11RelocWithPFEv+0x646>
  3cf35f:	48 8b 07             	mov    (%rdi),%rax
  3cf362:	48 8b 35 67 a6 52 00 	mov    0x52a667(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3cf369:	ff 50 20             	call   *0x20(%rax)
  3cf36c:	49 89 c4             	mov    %rax,%r12
  3cf36f:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3cf374:	eb 06                	jmp    3cf37c <_ZN5MCLoc11RelocWithPFEv+0x64c>
  3cf376:	45 31 ff             	xor    %r15d,%r15d
  3cf379:	45 31 e4             	xor    %r12d,%r12d
  3cf37c:	4c 89 64 24 48       	mov    %r12,0x48(%rsp)
  3cf381:	4d 85 ff             	test   %r15,%r15
  3cf384:	0f 84 d9 00 00 00    	je     3cf463 <_ZN5MCLoc11RelocWithPFEv+0x733>
  3cf38a:	48 83 3d 9e a7 52 00 	cmpq   $0x0,0x52a79e(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cf391:	00 
  3cf392:	0f 84 c6 00 00 00    	je     3cf45e <_ZN5MCLoc11RelocWithPFEv+0x72e>
  3cf398:	f0 41 83 47 08 01    	lock addl $0x1,0x8(%r15)
  3cf39e:	e9 c0 00 00 00       	jmp    3cf463 <_ZN5MCLoc11RelocWithPFEv+0x733>
  3cf3a3:	41 83 45 08 01       	addl   $0x1,0x8(%r13)
  3cf3a8:	48 c7 44 24 38 00 00 	movq   $0x0,0x38(%rsp)
  3cf3af:	00 00 
  3cf3b1:	bf 10 00 00 00       	mov    $0x10,%edi
  3cf3b6:	e8 a5 7e de ff       	call   1b7260 <_Znwm@plt>
  3cf3bb:	4c 89 38             	mov    %r15,(%rax)
  3cf3be:	4c 89 68 08          	mov    %r13,0x8(%rax)
  3cf3c2:	48 89 44 24 28       	mov    %rax,0x28(%rsp)
  3cf3c7:	48 8d 05 b2 2c 01 00 	lea    0x12cb2(%rip),%rax        # 3e2080 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_15JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3cf3ce:	48 89 44 24 40       	mov    %rax,0x40(%rsp)
  3cf3d3:	48 8d 05 d6 2c 01 00 	lea    0x12cd6(%rip),%rax        # 3e20b0 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_15JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3cf3da:	48 89 44 24 38       	mov    %rax,0x38(%rsp)
  3cf3df:	49 8d 7c 24 08       	lea    0x8(%r12),%rdi
  3cf3e4:	48 8d 74 24 28       	lea    0x28(%rsp),%rsi
  3cf3e9:	e8 12 2a de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3cf3ee:	49 81 c4 c0 01 00 00 	add    $0x1c0,%r12
  3cf3f5:	4c 89 e7             	mov    %r12,%rdi
  3cf3f8:	e8 73 8d de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3cf3fd:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3cf402:	48 8d bc 24 58 03 00 	lea    0x358(%rsp),%rdi
  3cf409:	00 
  3cf40a:	e8 c1 9c de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3cf40f:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3cf414:	48 85 c0             	test   %rax,%rax
  3cf417:	74 0f                	je     3cf428 <_ZN5MCLoc11RelocWithPFEv+0x6f8>
  3cf419:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3cf41e:	ba 03 00 00 00       	mov    $0x3,%edx
  3cf423:	48 89 fe             	mov    %rdi,%rsi
  3cf426:	ff d0                	call   *%rax
  3cf428:	4c 8b 64 24 50       	mov    0x50(%rsp),%r12
  3cf42d:	4d 85 e4             	test   %r12,%r12
  3cf430:	0f 84 7e 01 00 00    	je     3cf5b4 <_ZN5MCLoc11RelocWithPFEv+0x884>
  3cf436:	48 83 3d f2 a6 52 00 	cmpq   $0x0,0x52a6f2(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cf43d:	00 
  3cf43e:	0f 84 d3 00 00 00    	je     3cf517 <_ZN5MCLoc11RelocWithPFEv+0x7e7>
  3cf444:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cf449:	f0 41 0f c1 44 24 08 	lock xadd %eax,0x8(%r12)
  3cf450:	83 f8 01             	cmp    $0x1,%eax
  3cf453:	0f 84 d4 00 00 00    	je     3cf52d <_ZN5MCLoc11RelocWithPFEv+0x7fd>
  3cf459:	e9 56 01 00 00       	jmp    3cf5b4 <_ZN5MCLoc11RelocWithPFEv+0x884>
  3cf45e:	41 83 47 08 01       	addl   $0x1,0x8(%r15)
  3cf463:	48 c7 44 24 38 00 00 	movq   $0x0,0x38(%rsp)
  3cf46a:	00 00 
  3cf46c:	bf 10 00 00 00       	mov    $0x10,%edi
  3cf471:	e8 ea 7d de ff       	call   1b7260 <_Znwm@plt>
  3cf476:	4c 89 20             	mov    %r12,(%rax)
  3cf479:	4c 89 78 08          	mov    %r15,0x8(%rax)
  3cf47d:	48 89 44 24 28       	mov    %rax,0x28(%rsp)
  3cf482:	48 8d 05 b7 11 01 00 	lea    0x111b7(%rip),%rax        # 3e0640 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE3$_9JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3cf489:	48 89 44 24 40       	mov    %rax,0x40(%rsp)
  3cf48e:	48 8d 05 db 11 01 00 	lea    0x111db(%rip),%rax        # 3e0670 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE3$_9JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3cf495:	48 89 44 24 38       	mov    %rax,0x38(%rsp)
  3cf49a:	49 8d 7d 08          	lea    0x8(%r13),%rdi
  3cf49e:	48 8d 74 24 28       	lea    0x28(%rsp),%rsi
  3cf4a3:	e8 58 29 de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3cf4a8:	49 81 c5 c0 01 00 00 	add    $0x1c0,%r13
  3cf4af:	4c 89 ef             	mov    %r13,%rdi
  3cf4b2:	e8 b9 8c de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3cf4b7:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3cf4bc:	48 8d bc 24 b8 03 00 	lea    0x3b8(%rsp),%rdi
  3cf4c3:	00 
  3cf4c4:	e8 07 9c de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3cf4c9:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3cf4ce:	48 85 c0             	test   %rax,%rax
  3cf4d1:	4c 8b a4 24 e8 00 00 	mov    0xe8(%rsp),%r12
  3cf4d8:	00 
  3cf4d9:	74 0f                	je     3cf4ea <_ZN5MCLoc11RelocWithPFEv+0x7ba>
  3cf4db:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3cf4e0:	ba 03 00 00 00       	mov    $0x3,%edx
  3cf4e5:	48 89 fe             	mov    %rdi,%rsi
  3cf4e8:	ff d0                	call   *%rax
  3cf4ea:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3cf4ef:	4d 85 ff             	test   %r15,%r15
  3cf4f2:	0f 84 67 01 00 00    	je     3cf65f <_ZN5MCLoc11RelocWithPFEv+0x92f>
  3cf4f8:	48 83 3d 30 a6 52 00 	cmpq   $0x0,0x52a630(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cf4ff:	00 
  3cf500:	74 52                	je     3cf554 <_ZN5MCLoc11RelocWithPFEv+0x824>
  3cf502:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cf507:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3cf50d:	83 f8 01             	cmp    $0x1,%eax
  3cf510:	74 56                	je     3cf568 <_ZN5MCLoc11RelocWithPFEv+0x838>
  3cf512:	e9 48 01 00 00       	jmp    3cf65f <_ZN5MCLoc11RelocWithPFEv+0x92f>
  3cf517:	41 8b 44 24 08       	mov    0x8(%r12),%eax
  3cf51c:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cf51f:	41 89 4c 24 08       	mov    %ecx,0x8(%r12)
  3cf524:	83 f8 01             	cmp    $0x1,%eax
  3cf527:	0f 85 87 00 00 00    	jne    3cf5b4 <_ZN5MCLoc11RelocWithPFEv+0x884>
  3cf52d:	49 8b 04 24          	mov    (%r12),%rax
  3cf531:	4c 89 e7             	mov    %r12,%rdi
  3cf534:	ff 50 10             	call   *0x10(%rax)
  3cf537:	48 83 3d f1 a5 52 00 	cmpq   $0x0,0x52a5f1(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cf53e:	00 
  3cf53f:	74 57                	je     3cf598 <_ZN5MCLoc11RelocWithPFEv+0x868>
  3cf541:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cf546:	f0 41 0f c1 44 24 0c 	lock xadd %eax,0xc(%r12)
  3cf54d:	83 f8 01             	cmp    $0x1,%eax
  3cf550:	74 58                	je     3cf5aa <_ZN5MCLoc11RelocWithPFEv+0x87a>
  3cf552:	eb 60                	jmp    3cf5b4 <_ZN5MCLoc11RelocWithPFEv+0x884>
  3cf554:	41 8b 47 08          	mov    0x8(%r15),%eax
  3cf558:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cf55b:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3cf55f:	83 f8 01             	cmp    $0x1,%eax
  3cf562:	0f 85 f7 00 00 00    	jne    3cf65f <_ZN5MCLoc11RelocWithPFEv+0x92f>
  3cf568:	49 8b 07             	mov    (%r15),%rax
  3cf56b:	4c 89 ff             	mov    %r15,%rdi
  3cf56e:	ff 50 10             	call   *0x10(%rax)
  3cf571:	48 83 3d b7 a5 52 00 	cmpq   $0x0,0x52a5b7(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cf578:	00 
  3cf579:	0f 84 c7 00 00 00    	je     3cf646 <_ZN5MCLoc11RelocWithPFEv+0x916>
  3cf57f:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cf584:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3cf58a:	83 f8 01             	cmp    $0x1,%eax
  3cf58d:	0f 84 c3 00 00 00    	je     3cf656 <_ZN5MCLoc11RelocWithPFEv+0x926>
  3cf593:	e9 c7 00 00 00       	jmp    3cf65f <_ZN5MCLoc11RelocWithPFEv+0x92f>
  3cf598:	41 8b 44 24 0c       	mov    0xc(%r12),%eax
  3cf59d:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cf5a0:	41 89 4c 24 0c       	mov    %ecx,0xc(%r12)
  3cf5a5:	83 f8 01             	cmp    $0x1,%eax
  3cf5a8:	75 0a                	jne    3cf5b4 <_ZN5MCLoc11RelocWithPFEv+0x884>
  3cf5aa:	49 8b 04 24          	mov    (%r12),%rax
  3cf5ae:	4c 89 e7             	mov    %r12,%rdi
  3cf5b1:	ff 50 18             	call   *0x18(%rax)
  3cf5b4:	48 8b 44 24 78       	mov    0x78(%rsp),%rax
  3cf5b9:	48 85 c0             	test   %rax,%rax
  3cf5bc:	74 0f                	je     3cf5cd <_ZN5MCLoc11RelocWithPFEv+0x89d>
  3cf5be:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3cf5c3:	ba 03 00 00 00       	mov    $0x3,%edx
  3cf5c8:	48 89 fe             	mov    %rdi,%rsi
  3cf5cb:	ff d0                	call   *%rax
  3cf5cd:	4c 8b a4 24 60 03 00 	mov    0x360(%rsp),%r12
  3cf5d4:	00 
  3cf5d5:	4d 85 e4             	test   %r12,%r12
  3cf5d8:	0f 84 2a 01 00 00    	je     3cf708 <_ZN5MCLoc11RelocWithPFEv+0x9d8>
  3cf5de:	48 83 3d 4a a5 52 00 	cmpq   $0x0,0x52a54a(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cf5e5:	00 
  3cf5e6:	74 16                	je     3cf5fe <_ZN5MCLoc11RelocWithPFEv+0x8ce>
  3cf5e8:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cf5ed:	f0 41 0f c1 44 24 08 	lock xadd %eax,0x8(%r12)
  3cf5f4:	83 f8 01             	cmp    $0x1,%eax
  3cf5f7:	74 1b                	je     3cf614 <_ZN5MCLoc11RelocWithPFEv+0x8e4>
  3cf5f9:	e9 0a 01 00 00       	jmp    3cf708 <_ZN5MCLoc11RelocWithPFEv+0x9d8>
  3cf5fe:	41 8b 44 24 08       	mov    0x8(%r12),%eax
  3cf603:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cf606:	41 89 4c 24 08       	mov    %ecx,0x8(%r12)
  3cf60b:	83 f8 01             	cmp    $0x1,%eax
  3cf60e:	0f 85 f4 00 00 00    	jne    3cf708 <_ZN5MCLoc11RelocWithPFEv+0x9d8>
  3cf614:	49 8b 04 24          	mov    (%r12),%rax
  3cf618:	4c 89 e7             	mov    %r12,%rdi
  3cf61b:	ff 50 10             	call   *0x10(%rax)
  3cf61e:	48 83 3d 0a a5 52 00 	cmpq   $0x0,0x52a50a(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cf625:	00 
  3cf626:	0f 84 c0 00 00 00    	je     3cf6ec <_ZN5MCLoc11RelocWithPFEv+0x9bc>
  3cf62c:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cf631:	f0 41 0f c1 44 24 0c 	lock xadd %eax,0xc(%r12)
  3cf638:	83 f8 01             	cmp    $0x1,%eax
  3cf63b:	0f 84 bd 00 00 00    	je     3cf6fe <_ZN5MCLoc11RelocWithPFEv+0x9ce>
  3cf641:	e9 c2 00 00 00       	jmp    3cf708 <_ZN5MCLoc11RelocWithPFEv+0x9d8>
  3cf646:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3cf64a:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cf64d:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3cf651:	83 f8 01             	cmp    $0x1,%eax
  3cf654:	75 09                	jne    3cf65f <_ZN5MCLoc11RelocWithPFEv+0x92f>
  3cf656:	49 8b 07             	mov    (%r15),%rax
  3cf659:	4c 89 ff             	mov    %r15,%rdi
  3cf65c:	ff 50 18             	call   *0x18(%rax)
  3cf65f:	48 8b 44 24 78       	mov    0x78(%rsp),%rax
  3cf664:	48 85 c0             	test   %rax,%rax
  3cf667:	74 0f                	je     3cf678 <_ZN5MCLoc11RelocWithPFEv+0x948>
  3cf669:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3cf66e:	ba 03 00 00 00       	mov    $0x3,%edx
  3cf673:	48 89 fe             	mov    %rdi,%rsi
  3cf676:	ff d0                	call   *%rax
  3cf678:	4c 8b bc 24 c0 03 00 	mov    0x3c0(%rsp),%r15
  3cf67f:	00 
  3cf680:	4d 85 ff             	test   %r15,%r15
  3cf683:	0f 84 39 05 00 00    	je     3cfbc2 <_ZN5MCLoc11RelocWithPFEv+0xe92>
  3cf689:	48 83 3d 9f a4 52 00 	cmpq   $0x0,0x52a49f(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cf690:	00 
  3cf691:	74 15                	je     3cf6a8 <_ZN5MCLoc11RelocWithPFEv+0x978>
  3cf693:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cf698:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3cf69e:	83 f8 01             	cmp    $0x1,%eax
  3cf6a1:	74 19                	je     3cf6bc <_ZN5MCLoc11RelocWithPFEv+0x98c>
  3cf6a3:	e9 1a 05 00 00       	jmp    3cfbc2 <_ZN5MCLoc11RelocWithPFEv+0xe92>
  3cf6a8:	41 8b 47 08          	mov    0x8(%r15),%eax
  3cf6ac:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cf6af:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3cf6b3:	83 f8 01             	cmp    $0x1,%eax
  3cf6b6:	0f 85 06 05 00 00    	jne    3cfbc2 <_ZN5MCLoc11RelocWithPFEv+0xe92>
  3cf6bc:	49 8b 07             	mov    (%r15),%rax
  3cf6bf:	4c 89 ff             	mov    %r15,%rdi
  3cf6c2:	ff 50 10             	call   *0x10(%rax)
  3cf6c5:	48 83 3d 63 a4 52 00 	cmpq   $0x0,0x52a463(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cf6cc:	00 
  3cf6cd:	0f 84 d6 04 00 00    	je     3cfba9 <_ZN5MCLoc11RelocWithPFEv+0xe79>
  3cf6d3:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cf6d8:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3cf6de:	83 f8 01             	cmp    $0x1,%eax
  3cf6e1:	0f 84 d2 04 00 00    	je     3cfbb9 <_ZN5MCLoc11RelocWithPFEv+0xe89>
  3cf6e7:	e9 d6 04 00 00       	jmp    3cfbc2 <_ZN5MCLoc11RelocWithPFEv+0xe92>
  3cf6ec:	41 8b 44 24 0c       	mov    0xc(%r12),%eax
  3cf6f1:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cf6f4:	41 89 4c 24 0c       	mov    %ecx,0xc(%r12)
  3cf6f9:	83 f8 01             	cmp    $0x1,%eax
  3cf6fc:	75 0a                	jne    3cf708 <_ZN5MCLoc11RelocWithPFEv+0x9d8>
  3cf6fe:	49 8b 04 24          	mov    (%r12),%rax
  3cf702:	4c 89 e7             	mov    %r12,%rdi
  3cf705:	ff 50 18             	call   *0x18(%rax)
  3cf708:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3cf70d:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3cf712:	48 39 c7             	cmp    %rax,%rdi
  3cf715:	74 05                	je     3cf71c <_ZN5MCLoc11RelocWithPFEv+0x9ec>
  3cf717:	e8 d4 01 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cf71c:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3cf723:	00 
  3cf724:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3cf72b:	00 
  3cf72c:	48 39 c7             	cmp    %rax,%rdi
  3cf72f:	74 05                	je     3cf736 <_ZN5MCLoc11RelocWithPFEv+0xa06>
  3cf731:	e8 ba 01 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cf736:	4c 8b 35 8b b3 52 00 	mov    0x52b38b(%rip),%r14        # 8faac8 <_ZTTNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cf73d:	49 8b 06             	mov    (%r14),%rax
  3cf740:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3cf747:	00 
  3cf748:	49 8b 4e 40          	mov    0x40(%r14),%rcx
  3cf74c:	48 89 84 24 e0 00 00 	mov    %rax,0xe0(%rsp)
  3cf753:	00 
  3cf754:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cf758:	48 89 8c 24 d8 00 00 	mov    %rcx,0xd8(%rsp)
  3cf75f:	00 
  3cf760:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3cf767:	00 
  3cf768:	49 8b 46 48          	mov    0x48(%r14),%rax
  3cf76c:	48 89 84 24 d0 00 00 	mov    %rax,0xd0(%rsp)
  3cf773:	00 
  3cf774:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3cf77b:	00 
  3cf77c:	48 8b 05 6d 7b 52 00 	mov    0x527b6d(%rip),%rax        # 8f72f0 <_ZTVNSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cf783:	48 83 c0 10          	add    $0x10,%rax
  3cf787:	48 89 84 24 c8 00 00 	mov    %rax,0xc8(%rsp)
  3cf78e:	00 
  3cf78f:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3cf796:	00 
  3cf797:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3cf79e:	00 
  3cf79f:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3cf7a6:	00 
  3cf7a7:	48 39 c7             	cmp    %rax,%rdi
  3cf7aa:	74 05                	je     3cf7b1 <_ZN5MCLoc11RelocWithPFEv+0xa81>
  3cf7ac:	e8 3f 01 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cf7b1:	4c 8b 2d 98 92 52 00 	mov    0x529298(%rip),%r13        # 8f8a50 <_ZTVSt15basic_streambufIcSt11char_traitsIcEE@GLIBCXX_3.4>
  3cf7b8:	49 83 c5 10          	add    $0x10,%r13
  3cf7bc:	4c 89 ac 24 58 01 00 	mov    %r13,0x158(%rsp)
  3cf7c3:	00 
  3cf7c4:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3cf7cb:	00 
  3cf7cc:	e8 2f 43 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3cf7d1:	4d 8b 66 10          	mov    0x10(%r14),%r12
  3cf7d5:	4d 8b 76 18          	mov    0x18(%r14),%r14
  3cf7d9:	4c 89 a4 24 40 01 00 	mov    %r12,0x140(%rsp)
  3cf7e0:	00 
  3cf7e1:	49 8b 44 24 e8       	mov    -0x18(%r12),%rax
  3cf7e6:	4c 89 b4 04 40 01 00 	mov    %r14,0x140(%rsp,%rax,1)
  3cf7ed:	00 
  3cf7ee:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3cf7f5:	00 00 00 00 00 
  3cf7fa:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3cf801:	00 
  3cf802:	e8 b9 8e de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3cf807:	4c 8d bc 24 50 01 00 	lea    0x150(%rsp),%r15
  3cf80e:	00 
  3cf80f:	4c 89 bc 24 40 01 00 	mov    %r15,0x140(%rsp)
  3cf816:	00 
  3cf817:	48 b8 46 69 6e 69 73 	movabs $0x64656873696e6946,%rax
  3cf81e:	68 65 64 
  3cf821:	48 89 84 24 55 01 00 	mov    %rax,0x155(%rsp)
  3cf828:	00 
  3cf829:	48 b8 72 65 6c 6f 63 	movabs $0x6e6946636f6c6572,%rax
  3cf830:	46 69 6e 
  3cf833:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3cf83a:	00 
  3cf83b:	48 c7 84 24 48 01 00 	movq   $0xd,0x148(%rsp)
  3cf842:	00 0d 00 00 00 
  3cf847:	c6 84 24 5d 01 00 00 	movb   $0x0,0x15d(%rsp)
  3cf84e:	00 
  3cf84f:	48 8d b4 24 40 01 00 	lea    0x140(%rsp),%rsi
  3cf856:	00 
  3cf857:	48 8b bc 24 e8 00 00 	mov    0xe8(%rsp),%rdi
  3cf85e:	00 
  3cf85f:	e8 9c 97 de ff       	call   1b9000 <_ZN5MCLoc9FireEventERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE@plt>
  3cf864:	48 8b bc 24 40 01 00 	mov    0x140(%rsp),%rdi
  3cf86b:	00 
  3cf86c:	4c 39 ff             	cmp    %r15,%rdi
  3cf86f:	74 05                	je     3cf876 <_ZN5MCLoc11RelocWithPFEv+0xb46>
  3cf871:	e8 7a 00 de ff       	call   1af8f0 <_ZdlPv@plt>
  3cf876:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  3cf87d:	00 
  3cf87e:	be 18 00 00 00       	mov    $0x18,%esi
  3cf883:	e8 88 55 de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3cf888:	48 8d bc 24 50 01 00 	lea    0x150(%rsp),%rdi
  3cf88f:	00 
  3cf890:	48 8d 35 f1 14 1a 00 	lea    0x1a14f1(%rip),%rsi        # 570d88 <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc9FireEventERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEE4$_80JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x33e8>
  3cf897:	ba 0d 00 00 00       	mov    $0xd,%edx
  3cf89c:	4c 89 b4 24 b0 00 00 	mov    %r14,0xb0(%rsp)
  3cf8a3:	00 
  3cf8a4:	4c 89 a4 24 c0 00 00 	mov    %r12,0xc0(%rsp)
  3cf8ab:	00 
  3cf8ac:	4c 89 ac 24 b8 00 00 	mov    %r13,0xb8(%rsp)
  3cf8b3:	00 
  3cf8b4:	e8 37 12 de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3cf8b9:	48 8d b4 24 58 01 00 	lea    0x158(%rsp),%rsi
  3cf8c0:	00 
  3cf8c1:	48 8d bc 24 90 00 00 	lea    0x90(%rsp),%rdi
  3cf8c8:	00 
  3cf8c9:	e8 92 53 de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3cf8ce:	e8 0d 80 de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3cf8d3:	49 89 c7             	mov    %rax,%r15
  3cf8d6:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3cf8db:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3cf8e0:	4c 8b ac 24 90 00 00 	mov    0x90(%rsp),%r13
  3cf8e7:	00 
  3cf8e8:	4c 8b a4 24 98 00 00 	mov    0x98(%rsp),%r12
  3cf8ef:	00 
  3cf8f0:	4d 85 ed             	test   %r13,%r13
  3cf8f3:	75 09                	jne    3cf8fe <_ZN5MCLoc11RelocWithPFEv+0xbce>
  3cf8f5:	4d 85 e4             	test   %r12,%r12
  3cf8f8:	0f 85 fb 22 00 00    	jne    3d1bf9 <_ZN5MCLoc11RelocWithPFEv+0x2ec9>
  3cf8fe:	49 89 ce             	mov    %rcx,%r14
  3cf901:	49 83 fc 10          	cmp    $0x10,%r12
  3cf905:	72 25                	jb     3cf92c <_ZN5MCLoc11RelocWithPFEv+0xbfc>
  3cf907:	4d 85 e4             	test   %r12,%r12
  3cf90a:	0f 88 19 23 00 00    	js     3d1c29 <_ZN5MCLoc11RelocWithPFEv+0x2ef9>
  3cf910:	49 8d 7c 24 01       	lea    0x1(%r12),%rdi
  3cf915:	e8 46 79 de ff       	call   1b7260 <_Znwm@plt>
  3cf91a:	49 89 c6             	mov    %rax,%r14
  3cf91d:	4c 89 74 24 08       	mov    %r14,0x8(%rsp)
  3cf922:	4c 89 64 24 18       	mov    %r12,0x18(%rsp)
  3cf927:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3cf92c:	4d 85 e4             	test   %r12,%r12
  3cf92f:	74 22                	je     3cf953 <_ZN5MCLoc11RelocWithPFEv+0xc23>
  3cf931:	49 83 fc 01          	cmp    $0x1,%r12
  3cf935:	75 09                	jne    3cf940 <_ZN5MCLoc11RelocWithPFEv+0xc10>
  3cf937:	41 8a 45 00          	mov    0x0(%r13),%al
  3cf93b:	41 88 06             	mov    %al,(%r14)
  3cf93e:	eb 13                	jmp    3cf953 <_ZN5MCLoc11RelocWithPFEv+0xc23>
  3cf940:	4c 89 f7             	mov    %r14,%rdi
  3cf943:	4c 89 ee             	mov    %r13,%rsi
  3cf946:	4c 89 e2             	mov    %r12,%rdx
  3cf949:	e8 32 76 de ff       	call   1b6f80 <memcpy@plt>
  3cf94e:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3cf953:	4c 89 64 24 10       	mov    %r12,0x10(%rsp)
  3cf958:	43 c6 04 26 00       	movb   $0x0,(%r14,%r12,1)
  3cf95d:	4c 8d ac 24 00 01 00 	lea    0x100(%rsp),%r13
  3cf964:	00 
  3cf965:	4c 89 ac 24 f0 00 00 	mov    %r13,0xf0(%rsp)
  3cf96c:	00 
  3cf96d:	4c 8b 64 24 08       	mov    0x8(%rsp),%r12
  3cf972:	49 39 cc             	cmp    %rcx,%r12
  3cf975:	74 17                	je     3cf98e <_ZN5MCLoc11RelocWithPFEv+0xc5e>
  3cf977:	4c 89 a4 24 f0 00 00 	mov    %r12,0xf0(%rsp)
  3cf97e:	00 
  3cf97f:	48 8b 44 24 18       	mov    0x18(%rsp),%rax
  3cf984:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  3cf98b:	00 
  3cf98c:	eb 0d                	jmp    3cf99b <_ZN5MCLoc11RelocWithPFEv+0xc6b>
  3cf98e:	66 0f 10 01          	movupd (%rcx),%xmm0
  3cf992:	66 41 0f 11 45 00    	movupd %xmm0,0x0(%r13)
  3cf998:	4d 89 ec             	mov    %r13,%r12
  3cf99b:	4c 8b 74 24 10       	mov    0x10(%rsp),%r14
  3cf9a0:	4c 89 b4 24 f8 00 00 	mov    %r14,0xf8(%rsp)
  3cf9a7:	00 
  3cf9a8:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3cf9ad:	48 c7 44 24 10 00 00 	movq   $0x0,0x10(%rsp)
  3cf9b4:	00 00 
  3cf9b6:	c6 44 24 18 00       	movb   $0x0,0x18(%rsp)
  3cf9bb:	48 c7 44 24 78 00 00 	movq   $0x0,0x78(%rsp)
  3cf9c2:	00 00 
  3cf9c4:	bf 28 00 00 00       	mov    $0x28,%edi
  3cf9c9:	e8 92 78 de ff       	call   1b7260 <_Znwm@plt>
  3cf9ce:	48 89 c1             	mov    %rax,%rcx
  3cf9d1:	48 83 c1 10          	add    $0x10,%rcx
  3cf9d5:	48 89 08             	mov    %rcx,(%rax)
  3cf9d8:	4d 39 ec             	cmp    %r13,%r12
  3cf9db:	74 11                	je     3cf9ee <_ZN5MCLoc11RelocWithPFEv+0xcbe>
  3cf9dd:	4c 89 20             	mov    %r12,(%rax)
  3cf9e0:	48 8b 8c 24 00 01 00 	mov    0x100(%rsp),%rcx
  3cf9e7:	00 
  3cf9e8:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3cf9ec:	eb 0a                	jmp    3cf9f8 <_ZN5MCLoc11RelocWithPFEv+0xcc8>
  3cf9ee:	66 41 0f 10 45 00    	movupd 0x0(%r13),%xmm0
  3cf9f4:	66 0f 11 01          	movupd %xmm0,(%rcx)
  3cf9f8:	4c 89 ac 24 f0 00 00 	mov    %r13,0xf0(%rsp)
  3cf9ff:	00 
  3cfa00:	48 c7 84 24 f8 00 00 	movq   $0x0,0xf8(%rsp)
  3cfa07:	00 00 00 00 00 
  3cfa0c:	c6 84 24 00 01 00 00 	movb   $0x0,0x100(%rsp)
  3cfa13:	00 
  3cfa14:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3cfa18:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cfa1d:	48 8d 05 ac 27 01 00 	lea    0x127ac(%rip),%rax        # 3e21d0 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc11RelocWithPFEvE4$_16vEEE9_M_invokeERKSt9_Any_data>
  3cfa24:	48 89 84 24 80 00 00 	mov    %rax,0x80(%rsp)
  3cfa2b:	00 
  3cfa2c:	48 8d 05 7d 29 01 00 	lea    0x1297d(%rip),%rax        # 3e23b0 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc11RelocWithPFEvE4$_16vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3cfa33:	48 89 44 24 78       	mov    %rax,0x78(%rsp)
  3cfa38:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3cfa3f:	00 00 
  3cfa41:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3cfa46:	48 8d 54 24 28       	lea    0x28(%rsp),%rdx
  3cfa4b:	48 8d 4c 24 68       	lea    0x68(%rsp),%rcx
  3cfa50:	31 f6                	xor    %esi,%esi
  3cfa52:	e8 39 42 de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3cfa57:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3cfa5c:	48 85 ff             	test   %rdi,%rdi
  3cfa5f:	74 17                	je     3cfa78 <_ZN5MCLoc11RelocWithPFEv+0xd48>
  3cfa61:	48 8b 07             	mov    (%rdi),%rax
  3cfa64:	48 8b 35 65 9f 52 00 	mov    0x529f65(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3cfa6b:	ff 50 20             	call   *0x20(%rax)
  3cfa6e:	49 89 c5             	mov    %rax,%r13
  3cfa71:	4c 8b 64 24 50       	mov    0x50(%rsp),%r12
  3cfa76:	eb 06                	jmp    3cfa7e <_ZN5MCLoc11RelocWithPFEv+0xd4e>
  3cfa78:	45 31 e4             	xor    %r12d,%r12d
  3cfa7b:	45 31 ed             	xor    %r13d,%r13d
  3cfa7e:	4c 89 6c 24 48       	mov    %r13,0x48(%rsp)
  3cfa83:	4d 85 e4             	test   %r12,%r12
  3cfa86:	74 19                	je     3cfaa1 <_ZN5MCLoc11RelocWithPFEv+0xd71>
  3cfa88:	48 83 3d a0 a0 52 00 	cmpq   $0x0,0x52a0a0(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cfa8f:	00 
  3cfa90:	74 09                	je     3cfa9b <_ZN5MCLoc11RelocWithPFEv+0xd6b>
  3cfa92:	f0 41 83 44 24 08 01 	lock addl $0x1,0x8(%r12)
  3cfa99:	eb 06                	jmp    3cfaa1 <_ZN5MCLoc11RelocWithPFEv+0xd71>
  3cfa9b:	41 83 44 24 08 01    	addl   $0x1,0x8(%r12)
  3cfaa1:	48 c7 44 24 38 00 00 	movq   $0x0,0x38(%rsp)
  3cfaa8:	00 00 
  3cfaaa:	bf 10 00 00 00       	mov    $0x10,%edi
  3cfaaf:	e8 ac 77 de ff       	call   1b7260 <_Znwm@plt>
  3cfab4:	4c 89 28             	mov    %r13,(%rax)
  3cfab7:	4c 89 60 08          	mov    %r12,0x8(%rax)
  3cfabb:	48 89 44 24 28       	mov    %rax,0x28(%rsp)
  3cfac0:	48 8d 05 19 2a 01 00 	lea    0x12a19(%rip),%rax        # 3e24e0 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_16JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3cfac7:	48 89 44 24 40       	mov    %rax,0x40(%rsp)
  3cfacc:	48 8d 05 3d 2a 01 00 	lea    0x12a3d(%rip),%rax        # 3e2510 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_16JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3cfad3:	48 89 44 24 38       	mov    %rax,0x38(%rsp)
  3cfad8:	49 8d 7f 08          	lea    0x8(%r15),%rdi
  3cfadc:	48 8d 74 24 28       	lea    0x28(%rsp),%rsi
  3cfae1:	e8 1a 23 de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3cfae6:	49 81 c7 c0 01 00 00 	add    $0x1c0,%r15
  3cfaed:	4c 89 ff             	mov    %r15,%rdi
  3cfaf0:	e8 7b 86 de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3cfaf5:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3cfafa:	48 8d bc 24 48 03 00 	lea    0x348(%rsp),%rdi
  3cfb01:	00 
  3cfb02:	e8 c9 95 de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3cfb07:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3cfb0c:	48 85 c0             	test   %rax,%rax
  3cfb0f:	4c 8b b4 24 e8 00 00 	mov    0xe8(%rsp),%r14
  3cfb16:	00 
  3cfb17:	4c 8b a4 24 c0 00 00 	mov    0xc0(%rsp),%r12
  3cfb1e:	00 
  3cfb1f:	4c 8b ac 24 b8 00 00 	mov    0xb8(%rsp),%r13
  3cfb26:	00 
  3cfb27:	74 0f                	je     3cfb38 <_ZN5MCLoc11RelocWithPFEv+0xe08>
  3cfb29:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3cfb2e:	ba 03 00 00 00       	mov    $0x3,%edx
  3cfb33:	48 89 fe             	mov    %rdi,%rsi
  3cfb36:	ff d0                	call   *%rax
  3cfb38:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3cfb3d:	4d 85 ff             	test   %r15,%r15
  3cfb40:	0f 84 10 06 00 00    	je     3d0156 <_ZN5MCLoc11RelocWithPFEv+0x1426>
  3cfb46:	48 83 3d e2 9f 52 00 	cmpq   $0x0,0x529fe2(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cfb4d:	00 
  3cfb4e:	74 15                	je     3cfb65 <_ZN5MCLoc11RelocWithPFEv+0xe35>
  3cfb50:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cfb55:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3cfb5b:	83 f8 01             	cmp    $0x1,%eax
  3cfb5e:	74 19                	je     3cfb79 <_ZN5MCLoc11RelocWithPFEv+0xe49>
  3cfb60:	e9 f1 05 00 00       	jmp    3d0156 <_ZN5MCLoc11RelocWithPFEv+0x1426>
  3cfb65:	41 8b 47 08          	mov    0x8(%r15),%eax
  3cfb69:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cfb6c:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3cfb70:	83 f8 01             	cmp    $0x1,%eax
  3cfb73:	0f 85 dd 05 00 00    	jne    3d0156 <_ZN5MCLoc11RelocWithPFEv+0x1426>
  3cfb79:	49 8b 07             	mov    (%r15),%rax
  3cfb7c:	4c 89 ff             	mov    %r15,%rdi
  3cfb7f:	ff 50 10             	call   *0x10(%rax)
  3cfb82:	48 83 3d a6 9f 52 00 	cmpq   $0x0,0x529fa6(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cfb89:	00 
  3cfb8a:	0f 84 ad 05 00 00    	je     3d013d <_ZN5MCLoc11RelocWithPFEv+0x140d>
  3cfb90:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3cfb95:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3cfb9b:	83 f8 01             	cmp    $0x1,%eax
  3cfb9e:	0f 84 a9 05 00 00    	je     3d014d <_ZN5MCLoc11RelocWithPFEv+0x141d>
  3cfba4:	e9 ad 05 00 00       	jmp    3d0156 <_ZN5MCLoc11RelocWithPFEv+0x1426>
  3cfba9:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3cfbad:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3cfbb0:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3cfbb4:	83 f8 01             	cmp    $0x1,%eax
  3cfbb7:	75 09                	jne    3cfbc2 <_ZN5MCLoc11RelocWithPFEv+0xe92>
  3cfbb9:	49 8b 07             	mov    (%r15),%rax
  3cfbbc:	4c 89 ff             	mov    %r15,%rdi
  3cfbbf:	ff 50 18             	call   *0x18(%rax)
  3cfbc2:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3cfbc7:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3cfbcc:	48 39 c7             	cmp    %rax,%rdi
  3cfbcf:	74 05                	je     3cfbd6 <_ZN5MCLoc11RelocWithPFEv+0xea6>
  3cfbd1:	e8 1a fd dd ff       	call   1af8f0 <_ZdlPv@plt>
  3cfbd6:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3cfbdd:	00 
  3cfbde:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3cfbe5:	00 
  3cfbe6:	48 39 c7             	cmp    %rax,%rdi
  3cfbe9:	74 05                	je     3cfbf0 <_ZN5MCLoc11RelocWithPFEv+0xec0>
  3cfbeb:	e8 00 fd dd ff       	call   1af8f0 <_ZdlPv@plt>
  3cfbf0:	4c 8b 35 d1 ae 52 00 	mov    0x52aed1(%rip),%r14        # 8faac8 <_ZTTNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cfbf7:	49 8b 06             	mov    (%r14),%rax
  3cfbfa:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3cfc01:	00 
  3cfc02:	49 8b 4e 40          	mov    0x40(%r14),%rcx
  3cfc06:	48 89 84 24 b0 00 00 	mov    %rax,0xb0(%rsp)
  3cfc0d:	00 
  3cfc0e:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cfc12:	48 89 8c 24 b8 00 00 	mov    %rcx,0xb8(%rsp)
  3cfc19:	00 
  3cfc1a:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3cfc21:	00 
  3cfc22:	49 8b 46 48          	mov    0x48(%r14),%rax
  3cfc26:	48 89 84 24 c0 00 00 	mov    %rax,0xc0(%rsp)
  3cfc2d:	00 
  3cfc2e:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3cfc35:	00 
  3cfc36:	48 8b 05 b3 76 52 00 	mov    0x5276b3(%rip),%rax        # 8f72f0 <_ZTVNSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3cfc3d:	48 83 c0 10          	add    $0x10,%rax
  3cfc41:	48 89 84 24 c8 00 00 	mov    %rax,0xc8(%rsp)
  3cfc48:	00 
  3cfc49:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3cfc50:	00 
  3cfc51:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3cfc58:	00 
  3cfc59:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3cfc60:	00 
  3cfc61:	48 39 c7             	cmp    %rax,%rdi
  3cfc64:	74 05                	je     3cfc6b <_ZN5MCLoc11RelocWithPFEv+0xf3b>
  3cfc66:	e8 85 fc dd ff       	call   1af8f0 <_ZdlPv@plt>
  3cfc6b:	48 8b 05 de 8d 52 00 	mov    0x528dde(%rip),%rax        # 8f8a50 <_ZTVSt15basic_streambufIcSt11char_traitsIcEE@GLIBCXX_3.4>
  3cfc72:	48 83 c0 10          	add    $0x10,%rax
  3cfc76:	48 89 84 24 d0 00 00 	mov    %rax,0xd0(%rsp)
  3cfc7d:	00 
  3cfc7e:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3cfc85:	00 
  3cfc86:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3cfc8d:	00 
  3cfc8e:	e8 6d 3e de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3cfc93:	49 8b 46 10          	mov    0x10(%r14),%rax
  3cfc97:	49 8b 4e 18          	mov    0x18(%r14),%rcx
  3cfc9b:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3cfca2:	00 
  3cfca3:	48 89 84 24 d8 00 00 	mov    %rax,0xd8(%rsp)
  3cfcaa:	00 
  3cfcab:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3cfcaf:	48 89 8c 24 e0 00 00 	mov    %rcx,0xe0(%rsp)
  3cfcb6:	00 
  3cfcb7:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3cfcbe:	00 
  3cfcbf:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3cfcc6:	00 00 00 00 00 
  3cfccb:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3cfcd2:	00 
  3cfcd3:	e8 e8 89 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3cfcd8:	41 8b 84 24 44 0f 00 	mov    0xf44(%r12),%eax
  3cfcdf:	00 
  3cfce0:	8d 48 01             	lea    0x1(%rax),%ecx
  3cfce3:	41 89 8c 24 44 0f 00 	mov    %ecx,0xf44(%r12)
  3cfcea:	00 
  3cfceb:	83 f8 63             	cmp    $0x63,%eax
  3cfcee:	7f 0f                	jg     3cfcff <_ZN5MCLoc11RelocWithPFEv+0xfcf>
  3cfcf0:	41 80 bc 24 67 18 00 	cmpb   $0x0,0x1867(%r12)
  3cfcf7:	00 00 
  3cfcf9:	0f 84 6f 03 00 00    	je     3d006e <_ZN5MCLoc11RelocWithPFEv+0x133e>
  3cfcff:	4c 8d b4 24 50 01 00 	lea    0x150(%rsp),%r14
  3cfd06:	00 
  3cfd07:	4c 89 b4 24 40 01 00 	mov    %r14,0x140(%rsp)
  3cfd0e:	00 
  3cfd0f:	48 b8 46 69 6e 69 73 	movabs $0x64656873696e6946,%rax
  3cfd16:	68 65 64 
  3cfd19:	48 89 84 24 55 01 00 	mov    %rax,0x155(%rsp)
  3cfd20:	00 
  3cfd21:	48 b8 72 65 6c 6f 63 	movabs $0x6e6946636f6c6572,%rax
  3cfd28:	46 69 6e 
  3cfd2b:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3cfd32:	00 
  3cfd33:	48 c7 84 24 48 01 00 	movq   $0xd,0x148(%rsp)
  3cfd3a:	00 0d 00 00 00 
  3cfd3f:	c6 84 24 5d 01 00 00 	movb   $0x0,0x15d(%rsp)
  3cfd46:	00 
  3cfd47:	48 8d b4 24 40 01 00 	lea    0x140(%rsp),%rsi
  3cfd4e:	00 
  3cfd4f:	4c 89 e7             	mov    %r12,%rdi
  3cfd52:	e8 a9 92 de ff       	call   1b9000 <_ZN5MCLoc9FireEventERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE@plt>
  3cfd57:	48 8b bc 24 40 01 00 	mov    0x140(%rsp),%rdi
  3cfd5e:	00 
  3cfd5f:	4c 39 f7             	cmp    %r14,%rdi
  3cfd62:	74 05                	je     3cfd69 <_ZN5MCLoc11RelocWithPFEv+0x1039>
  3cfd64:	e8 87 fb dd ff       	call   1af8f0 <_ZdlPv@plt>
  3cfd69:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  3cfd70:	00 
  3cfd71:	be 18 00 00 00       	mov    $0x18,%esi
  3cfd76:	e8 95 50 de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3cfd7b:	48 8d bc 24 50 01 00 	lea    0x150(%rsp),%rdi
  3cfd82:	00 
  3cfd83:	48 8d 35 fe 0f 1a 00 	lea    0x1a0ffe(%rip),%rsi        # 570d88 <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc9FireEventERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEE4$_80JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x33e8>
  3cfd8a:	ba 0d 00 00 00       	mov    $0xd,%edx
  3cfd8f:	e8 5c 0d de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3cfd94:	48 8d b4 24 58 01 00 	lea    0x158(%rsp),%rsi
  3cfd9b:	00 
  3cfd9c:	48 8d bc 24 90 00 00 	lea    0x90(%rsp),%rdi
  3cfda3:	00 
  3cfda4:	e8 b7 4e de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3cfda9:	e8 32 7b de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3cfdae:	49 89 c4             	mov    %rax,%r12
  3cfdb1:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3cfdb6:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3cfdbb:	4c 8b bc 24 90 00 00 	mov    0x90(%rsp),%r15
  3cfdc2:	00 
  3cfdc3:	4c 8b ac 24 98 00 00 	mov    0x98(%rsp),%r13
  3cfdca:	00 
  3cfdcb:	4d 85 ff             	test   %r15,%r15
  3cfdce:	75 09                	jne    3cfdd9 <_ZN5MCLoc11RelocWithPFEv+0x10a9>
  3cfdd0:	4d 85 ed             	test   %r13,%r13
  3cfdd3:	0f 85 2c 1e 00 00    	jne    3d1c05 <_ZN5MCLoc11RelocWithPFEv+0x2ed5>
  3cfdd9:	49 89 ce             	mov    %rcx,%r14
  3cfddc:	49 83 fd 10          	cmp    $0x10,%r13
  3cfde0:	72 24                	jb     3cfe06 <_ZN5MCLoc11RelocWithPFEv+0x10d6>
  3cfde2:	4d 85 ed             	test   %r13,%r13
  3cfde5:	0f 88 4a 1e 00 00    	js     3d1c35 <_ZN5MCLoc11RelocWithPFEv+0x2f05>
  3cfdeb:	49 8d 7d 01          	lea    0x1(%r13),%rdi
  3cfdef:	e8 6c 74 de ff       	call   1b7260 <_Znwm@plt>
  3cfdf4:	49 89 c6             	mov    %rax,%r14
  3cfdf7:	4c 89 74 24 08       	mov    %r14,0x8(%rsp)
  3cfdfc:	4c 89 6c 24 18       	mov    %r13,0x18(%rsp)
  3cfe01:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3cfe06:	4d 85 ed             	test   %r13,%r13
  3cfe09:	74 21                	je     3cfe2c <_ZN5MCLoc11RelocWithPFEv+0x10fc>
  3cfe0b:	49 83 fd 01          	cmp    $0x1,%r13
  3cfe0f:	75 08                	jne    3cfe19 <_ZN5MCLoc11RelocWithPFEv+0x10e9>
  3cfe11:	41 8a 07             	mov    (%r15),%al
  3cfe14:	41 88 06             	mov    %al,(%r14)
  3cfe17:	eb 13                	jmp    3cfe2c <_ZN5MCLoc11RelocWithPFEv+0x10fc>
  3cfe19:	4c 89 f7             	mov    %r14,%rdi
  3cfe1c:	4c 89 fe             	mov    %r15,%rsi
  3cfe1f:	4c 89 ea             	mov    %r13,%rdx
  3cfe22:	e8 59 71 de ff       	call   1b6f80 <memcpy@plt>
  3cfe27:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3cfe2c:	4c 89 6c 24 10       	mov    %r13,0x10(%rsp)
  3cfe31:	43 c6 04 2e 00       	movb   $0x0,(%r14,%r13,1)
  3cfe36:	4c 8d ac 24 00 01 00 	lea    0x100(%rsp),%r13
  3cfe3d:	00 
  3cfe3e:	4c 89 ac 24 f0 00 00 	mov    %r13,0xf0(%rsp)
  3cfe45:	00 
  3cfe46:	4c 8b 7c 24 08       	mov    0x8(%rsp),%r15
  3cfe4b:	49 39 cf             	cmp    %rcx,%r15
  3cfe4e:	74 17                	je     3cfe67 <_ZN5MCLoc11RelocWithPFEv+0x1137>
  3cfe50:	4c 89 bc 24 f0 00 00 	mov    %r15,0xf0(%rsp)
  3cfe57:	00 
  3cfe58:	48 8b 44 24 18       	mov    0x18(%rsp),%rax
  3cfe5d:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  3cfe64:	00 
  3cfe65:	eb 0d                	jmp    3cfe74 <_ZN5MCLoc11RelocWithPFEv+0x1144>
  3cfe67:	66 0f 10 01          	movupd (%rcx),%xmm0
  3cfe6b:	66 41 0f 11 45 00    	movupd %xmm0,0x0(%r13)
  3cfe71:	4d 89 ef             	mov    %r13,%r15
  3cfe74:	4c 8b 74 24 10       	mov    0x10(%rsp),%r14
  3cfe79:	4c 89 b4 24 f8 00 00 	mov    %r14,0xf8(%rsp)
  3cfe80:	00 
  3cfe81:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3cfe86:	48 c7 44 24 10 00 00 	movq   $0x0,0x10(%rsp)
  3cfe8d:	00 00 
  3cfe8f:	c6 44 24 18 00       	movb   $0x0,0x18(%rsp)
  3cfe94:	48 c7 44 24 78 00 00 	movq   $0x0,0x78(%rsp)
  3cfe9b:	00 00 
  3cfe9d:	bf 28 00 00 00       	mov    $0x28,%edi
  3cfea2:	e8 b9 73 de ff       	call   1b7260 <_Znwm@plt>
  3cfea7:	48 89 c1             	mov    %rax,%rcx
  3cfeaa:	48 83 c1 10          	add    $0x10,%rcx
  3cfeae:	48 89 08             	mov    %rcx,(%rax)
  3cfeb1:	4d 39 ef             	cmp    %r13,%r15
  3cfeb4:	74 11                	je     3cfec7 <_ZN5MCLoc11RelocWithPFEv+0x1197>
  3cfeb6:	4c 89 38             	mov    %r15,(%rax)
  3cfeb9:	48 8b 8c 24 00 01 00 	mov    0x100(%rsp),%rcx
  3cfec0:	00 
  3cfec1:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3cfec5:	eb 0a                	jmp    3cfed1 <_ZN5MCLoc11RelocWithPFEv+0x11a1>
  3cfec7:	66 41 0f 10 45 00    	movupd 0x0(%r13),%xmm0
  3cfecd:	66 0f 11 01          	movupd %xmm0,(%rcx)
  3cfed1:	4c 89 ac 24 f0 00 00 	mov    %r13,0xf0(%rsp)
  3cfed8:	00 
  3cfed9:	48 c7 84 24 f8 00 00 	movq   $0x0,0xf8(%rsp)
  3cfee0:	00 00 00 00 00 
  3cfee5:	c6 84 24 00 01 00 00 	movb   $0x0,0x100(%rsp)
  3cfeec:	00 
  3cfeed:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3cfef1:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3cfef6:	48 8d 05 f3 0c 01 00 	lea    0x10cf3(%rip),%rax        # 3e0bf0 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc11RelocWithPFEvE4$_11vEEE9_M_invokeERKSt9_Any_data>
  3cfefd:	48 89 84 24 80 00 00 	mov    %rax,0x80(%rsp)
  3cff04:	00 
  3cff05:	48 8d 05 c4 0e 01 00 	lea    0x10ec4(%rip),%rax        # 3e0dd0 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc11RelocWithPFEvE4$_11vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3cff0c:	48 89 44 24 78       	mov    %rax,0x78(%rsp)
  3cff11:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3cff18:	00 00 
  3cff1a:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3cff1f:	48 8d 54 24 28       	lea    0x28(%rsp),%rdx
  3cff24:	48 8d 4c 24 68       	lea    0x68(%rsp),%rcx
  3cff29:	31 f6                	xor    %esi,%esi
  3cff2b:	e8 60 3d de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3cff30:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3cff35:	48 85 ff             	test   %rdi,%rdi
  3cff38:	74 17                	je     3cff51 <_ZN5MCLoc11RelocWithPFEv+0x1221>
  3cff3a:	48 8b 07             	mov    (%rdi),%rax
  3cff3d:	48 8b 35 8c 9a 52 00 	mov    0x529a8c(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3cff44:	ff 50 20             	call   *0x20(%rax)
  3cff47:	49 89 c7             	mov    %rax,%r15
  3cff4a:	4c 8b 6c 24 50       	mov    0x50(%rsp),%r13
  3cff4f:	eb 06                	jmp    3cff57 <_ZN5MCLoc11RelocWithPFEv+0x1227>
  3cff51:	45 31 ed             	xor    %r13d,%r13d
  3cff54:	45 31 ff             	xor    %r15d,%r15d
  3cff57:	4c 89 7c 24 48       	mov    %r15,0x48(%rsp)
  3cff5c:	4d 85 ed             	test   %r13,%r13
  3cff5f:	74 17                	je     3cff78 <_ZN5MCLoc11RelocWithPFEv+0x1248>
  3cff61:	48 83 3d c7 9b 52 00 	cmpq   $0x0,0x529bc7(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3cff68:	00 
  3cff69:	74 08                	je     3cff73 <_ZN5MCLoc11RelocWithPFEv+0x1243>
  3cff6b:	f0 41 83 45 08 01    	lock addl $0x1,0x8(%r13)
  3cff71:	eb 05                	jmp    3cff78 <_ZN5MCLoc11RelocWithPFEv+0x1248>
  3cff73:	41 83 45 08 01       	addl   $0x1,0x8(%r13)
  3cff78:	48 c7 44 24 38 00 00 	movq   $0x0,0x38(%rsp)
  3cff7f:	00 00 
  3cff81:	bf 10 00 00 00       	mov    $0x10,%edi
  3cff86:	e8 d5 72 de ff       	call   1b7260 <_Znwm@plt>
  3cff8b:	4c 89 38             	mov    %r15,(%rax)
  3cff8e:	4c 89 68 08          	mov    %r13,0x8(%rax)
  3cff92:	48 89 44 24 28       	mov    %rax,0x28(%rsp)
  3cff97:	48 8d 05 62 0f 01 00 	lea    0x10f62(%rip),%rax        # 3e0f00 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_11JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3cff9e:	48 89 44 24 40       	mov    %rax,0x40(%rsp)
  3cffa3:	48 8d 05 86 0f 01 00 	lea    0x10f86(%rip),%rax        # 3e0f30 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_11JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3cffaa:	48 89 44 24 38       	mov    %rax,0x38(%rsp)
  3cffaf:	49 8d 7c 24 08       	lea    0x8(%r12),%rdi
  3cffb4:	48 8d 74 24 28       	lea    0x28(%rsp),%rsi
  3cffb9:	e8 42 1e de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3cffbe:	49 81 c4 c0 01 00 00 	add    $0x1c0,%r12
  3cffc5:	4c 89 e7             	mov    %r12,%rdi
  3cffc8:	e8 a3 81 de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3cffcd:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3cffd2:	48 8d bc 24 98 03 00 	lea    0x398(%rsp),%rdi
  3cffd9:	00 
  3cffda:	e8 f1 90 de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3cffdf:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3cffe4:	48 85 c0             	test   %rax,%rax
  3cffe7:	74 0f                	je     3cfff8 <_ZN5MCLoc11RelocWithPFEv+0x12c8>
  3cffe9:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3cffee:	ba 03 00 00 00       	mov    $0x3,%edx
  3cfff3:	48 89 fe             	mov    %rdi,%rsi
  3cfff6:	ff d0                	call   *%rax
  3cfff8:	4c 8b 64 24 50       	mov    0x50(%rsp),%r12
  3cfffd:	4d 85 e4             	test   %r12,%r12
  3d0000:	0f 84 f3 02 00 00    	je     3d02f9 <_ZN5MCLoc11RelocWithPFEv+0x15c9>
  3d0006:	48 83 3d 22 9b 52 00 	cmpq   $0x0,0x529b22(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d000d:	00 
  3d000e:	74 16                	je     3d0026 <_ZN5MCLoc11RelocWithPFEv+0x12f6>
  3d0010:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d0015:	f0 41 0f c1 44 24 08 	lock xadd %eax,0x8(%r12)
  3d001c:	83 f8 01             	cmp    $0x1,%eax
  3d001f:	74 1b                	je     3d003c <_ZN5MCLoc11RelocWithPFEv+0x130c>
  3d0021:	e9 d3 02 00 00       	jmp    3d02f9 <_ZN5MCLoc11RelocWithPFEv+0x15c9>
  3d0026:	41 8b 44 24 08       	mov    0x8(%r12),%eax
  3d002b:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d002e:	41 89 4c 24 08       	mov    %ecx,0x8(%r12)
  3d0033:	83 f8 01             	cmp    $0x1,%eax
  3d0036:	0f 85 bd 02 00 00    	jne    3d02f9 <_ZN5MCLoc11RelocWithPFEv+0x15c9>
  3d003c:	49 8b 04 24          	mov    (%r12),%rax
  3d0040:	4c 89 e7             	mov    %r12,%rdi
  3d0043:	ff 50 10             	call   *0x10(%rax)
  3d0046:	48 83 3d e2 9a 52 00 	cmpq   $0x0,0x529ae2(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d004d:	00 
  3d004e:	0f 84 89 02 00 00    	je     3d02dd <_ZN5MCLoc11RelocWithPFEv+0x15ad>
  3d0054:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d0059:	f0 41 0f c1 44 24 0c 	lock xadd %eax,0xc(%r12)
  3d0060:	83 f8 01             	cmp    $0x1,%eax
  3d0063:	0f 84 86 02 00 00    	je     3d02ef <_ZN5MCLoc11RelocWithPFEv+0x15bf>
  3d0069:	e9 8b 02 00 00       	jmp    3d02f9 <_ZN5MCLoc11RelocWithPFEv+0x15c9>
  3d006e:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  3d0075:	00 
  3d0076:	be 18 00 00 00       	mov    $0x18,%esi
  3d007b:	e8 90 4d de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3d0080:	4c 8d b4 24 50 01 00 	lea    0x150(%rsp),%r14
  3d0087:	00 
  3d0088:	48 8d 35 28 44 1f 00 	lea    0x1f4428(%rip),%rsi        # 5c44b7 <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc15SetGnssParticleERKNS_8protocol12Message_GNSSEE4$_43JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x227>
  3d008f:	ba 14 00 00 00       	mov    $0x14,%edx
  3d0094:	4c 89 f7             	mov    %r14,%rdi
  3d0097:	e8 54 0a de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3d009c:	41 8b b4 24 44 0f 00 	mov    0xf44(%r12),%esi
  3d00a3:	00 
  3d00a4:	4c 89 f7             	mov    %r14,%rdi
  3d00a7:	e8 34 21 de ff       	call   1b21e0 <_ZNSolsEi@plt>
  3d00ac:	48 8d b4 24 58 01 00 	lea    0x158(%rsp),%rsi
  3d00b3:	00 
  3d00b4:	48 8d bc 24 90 00 00 	lea    0x90(%rsp),%rdi
  3d00bb:	00 
  3d00bc:	e8 9f 4b de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3d00c1:	e8 1a 78 de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3d00c6:	49 89 c4             	mov    %rax,%r12
  3d00c9:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3d00ce:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3d00d3:	4c 8b ac 24 90 00 00 	mov    0x90(%rsp),%r13
  3d00da:	00 
  3d00db:	4c 8b bc 24 98 00 00 	mov    0x98(%rsp),%r15
  3d00e2:	00 
  3d00e3:	4d 85 ed             	test   %r13,%r13
  3d00e6:	75 09                	jne    3d00f1 <_ZN5MCLoc11RelocWithPFEv+0x13c1>
  3d00e8:	4d 85 ff             	test   %r15,%r15
  3d00eb:	0f 85 8c 1b 00 00    	jne    3d1c7d <_ZN5MCLoc11RelocWithPFEv+0x2f4d>
  3d00f1:	49 89 ce             	mov    %rcx,%r14
  3d00f4:	49 83 ff 10          	cmp    $0x10,%r15
  3d00f8:	72 24                	jb     3d011e <_ZN5MCLoc11RelocWithPFEv+0x13ee>
  3d00fa:	4d 85 ff             	test   %r15,%r15
  3d00fd:	0f 88 99 1b 00 00    	js     3d1c9c <_ZN5MCLoc11RelocWithPFEv+0x2f6c>
  3d0103:	49 8d 7f 01          	lea    0x1(%r15),%rdi
  3d0107:	e8 54 71 de ff       	call   1b7260 <_Znwm@plt>
  3d010c:	49 89 c6             	mov    %rax,%r14
  3d010f:	4c 89 74 24 08       	mov    %r14,0x8(%rsp)
  3d0114:	4c 89 7c 24 18       	mov    %r15,0x18(%rsp)
  3d0119:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3d011e:	4d 85 ff             	test   %r15,%r15
  3d0121:	0f 84 58 15 00 00    	je     3d167f <_ZN5MCLoc11RelocWithPFEv+0x294f>
  3d0127:	49 83 ff 01          	cmp    $0x1,%r15
  3d012b:	0f 85 3b 15 00 00    	jne    3d166c <_ZN5MCLoc11RelocWithPFEv+0x293c>
  3d0131:	41 8a 45 00          	mov    0x0(%r13),%al
  3d0135:	41 88 06             	mov    %al,(%r14)
  3d0138:	e9 42 15 00 00       	jmp    3d167f <_ZN5MCLoc11RelocWithPFEv+0x294f>
  3d013d:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d0141:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d0144:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d0148:	83 f8 01             	cmp    $0x1,%eax
  3d014b:	75 09                	jne    3d0156 <_ZN5MCLoc11RelocWithPFEv+0x1426>
  3d014d:	49 8b 07             	mov    (%r15),%rax
  3d0150:	4c 89 ff             	mov    %r15,%rdi
  3d0153:	ff 50 18             	call   *0x18(%rax)
  3d0156:	48 8b 44 24 78       	mov    0x78(%rsp),%rax
  3d015b:	48 85 c0             	test   %rax,%rax
  3d015e:	74 0f                	je     3d016f <_ZN5MCLoc11RelocWithPFEv+0x143f>
  3d0160:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3d0165:	ba 03 00 00 00       	mov    $0x3,%edx
  3d016a:	48 89 fe             	mov    %rdi,%rsi
  3d016d:	ff d0                	call   *%rax
  3d016f:	4c 8b bc 24 50 03 00 	mov    0x350(%rsp),%r15
  3d0176:	00 
  3d0177:	4d 85 ff             	test   %r15,%r15
  3d017a:	74 6a                	je     3d01e6 <_ZN5MCLoc11RelocWithPFEv+0x14b6>
  3d017c:	48 83 3d ac 99 52 00 	cmpq   $0x0,0x5299ac(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d0183:	00 
  3d0184:	74 12                	je     3d0198 <_ZN5MCLoc11RelocWithPFEv+0x1468>
  3d0186:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d018b:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d0191:	83 f8 01             	cmp    $0x1,%eax
  3d0194:	74 12                	je     3d01a8 <_ZN5MCLoc11RelocWithPFEv+0x1478>
  3d0196:	eb 4e                	jmp    3d01e6 <_ZN5MCLoc11RelocWithPFEv+0x14b6>
  3d0198:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d019c:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d019f:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d01a3:	83 f8 01             	cmp    $0x1,%eax
  3d01a6:	75 3e                	jne    3d01e6 <_ZN5MCLoc11RelocWithPFEv+0x14b6>
  3d01a8:	49 8b 07             	mov    (%r15),%rax
  3d01ab:	4c 89 ff             	mov    %r15,%rdi
  3d01ae:	ff 50 10             	call   *0x10(%rax)
  3d01b1:	48 83 3d 77 99 52 00 	cmpq   $0x0,0x529977(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d01b8:	00 
  3d01b9:	74 12                	je     3d01cd <_ZN5MCLoc11RelocWithPFEv+0x149d>
  3d01bb:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d01c0:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d01c6:	83 f8 01             	cmp    $0x1,%eax
  3d01c9:	74 12                	je     3d01dd <_ZN5MCLoc11RelocWithPFEv+0x14ad>
  3d01cb:	eb 19                	jmp    3d01e6 <_ZN5MCLoc11RelocWithPFEv+0x14b6>
  3d01cd:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d01d1:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d01d4:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d01d8:	83 f8 01             	cmp    $0x1,%eax
  3d01db:	75 09                	jne    3d01e6 <_ZN5MCLoc11RelocWithPFEv+0x14b6>
  3d01dd:	49 8b 07             	mov    (%r15),%rax
  3d01e0:	4c 89 ff             	mov    %r15,%rdi
  3d01e3:	ff 50 18             	call   *0x18(%rax)
  3d01e6:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d01eb:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d01f0:	48 39 c7             	cmp    %rax,%rdi
  3d01f3:	74 05                	je     3d01fa <_ZN5MCLoc11RelocWithPFEv+0x14ca>
  3d01f5:	e8 f6 f6 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d01fa:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3d0201:	00 
  3d0202:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3d0209:	00 
  3d020a:	48 39 c7             	cmp    %rax,%rdi
  3d020d:	74 05                	je     3d0214 <_ZN5MCLoc11RelocWithPFEv+0x14e4>
  3d020f:	e8 dc f6 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d0214:	48 8b 84 24 e0 00 00 	mov    0xe0(%rsp),%rax
  3d021b:	00 
  3d021c:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d0223:	00 
  3d0224:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d0228:	48 8b 8c 24 d8 00 00 	mov    0xd8(%rsp),%rcx
  3d022f:	00 
  3d0230:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d0237:	00 
  3d0238:	48 8b 84 24 d0 00 00 	mov    0xd0(%rsp),%rax
  3d023f:	00 
  3d0240:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d0247:	00 
  3d0248:	48 8b 84 24 c8 00 00 	mov    0xc8(%rsp),%rax
  3d024f:	00 
  3d0250:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d0257:	00 
  3d0258:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d025f:	00 
  3d0260:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d0267:	00 
  3d0268:	48 39 c7             	cmp    %rax,%rdi
  3d026b:	74 05                	je     3d0272 <_ZN5MCLoc11RelocWithPFEv+0x1542>
  3d026d:	e8 7e f6 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d0272:	4c 89 ac 24 58 01 00 	mov    %r13,0x158(%rsp)
  3d0279:	00 
  3d027a:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d0281:	00 
  3d0282:	e8 79 38 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d0287:	4c 89 a4 24 40 01 00 	mov    %r12,0x140(%rsp)
  3d028e:	00 
  3d028f:	49 8b 44 24 e8       	mov    -0x18(%r12),%rax
  3d0294:	48 8b 8c 24 b0 00 00 	mov    0xb0(%rsp),%rcx
  3d029b:	00 
  3d029c:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d02a3:	00 
  3d02a4:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d02ab:	00 00 00 00 00 
  3d02b0:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d02b7:	00 
  3d02b8:	e8 03 84 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3d02bd:	41 c7 86 5c 18 00 00 	movl   $0x2,0x185c(%r14)
  3d02c4:	02 00 00 00 
  3d02c8:	41 c6 86 67 18 00 00 	movb   $0x0,0x1867(%r14)
  3d02cf:	00 
  3d02d0:	41 c6 86 18 0f 00 00 	movb   $0x1,0xf18(%r14)
  3d02d7:	01 
  3d02d8:	e9 73 13 00 00       	jmp    3d1650 <_ZN5MCLoc11RelocWithPFEv+0x2920>
  3d02dd:	41 8b 44 24 0c       	mov    0xc(%r12),%eax
  3d02e2:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d02e5:	41 89 4c 24 0c       	mov    %ecx,0xc(%r12)
  3d02ea:	83 f8 01             	cmp    $0x1,%eax
  3d02ed:	75 0a                	jne    3d02f9 <_ZN5MCLoc11RelocWithPFEv+0x15c9>
  3d02ef:	49 8b 04 24          	mov    (%r12),%rax
  3d02f3:	4c 89 e7             	mov    %r12,%rdi
  3d02f6:	ff 50 18             	call   *0x18(%rax)
  3d02f9:	48 8b 44 24 78       	mov    0x78(%rsp),%rax
  3d02fe:	48 85 c0             	test   %rax,%rax
  3d0301:	74 0f                	je     3d0312 <_ZN5MCLoc11RelocWithPFEv+0x15e2>
  3d0303:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3d0308:	ba 03 00 00 00       	mov    $0x3,%edx
  3d030d:	48 89 fe             	mov    %rdi,%rsi
  3d0310:	ff d0                	call   *%rax
  3d0312:	4c 8b a4 24 a0 03 00 	mov    0x3a0(%rsp),%r12
  3d0319:	00 
  3d031a:	4d 85 e4             	test   %r12,%r12
  3d031d:	74 72                	je     3d0391 <_ZN5MCLoc11RelocWithPFEv+0x1661>
  3d031f:	48 83 3d 09 98 52 00 	cmpq   $0x0,0x529809(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d0326:	00 
  3d0327:	74 13                	je     3d033c <_ZN5MCLoc11RelocWithPFEv+0x160c>
  3d0329:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d032e:	f0 41 0f c1 44 24 08 	lock xadd %eax,0x8(%r12)
  3d0335:	83 f8 01             	cmp    $0x1,%eax
  3d0338:	74 14                	je     3d034e <_ZN5MCLoc11RelocWithPFEv+0x161e>
  3d033a:	eb 55                	jmp    3d0391 <_ZN5MCLoc11RelocWithPFEv+0x1661>
  3d033c:	41 8b 44 24 08       	mov    0x8(%r12),%eax
  3d0341:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d0344:	41 89 4c 24 08       	mov    %ecx,0x8(%r12)
  3d0349:	83 f8 01             	cmp    $0x1,%eax
  3d034c:	75 43                	jne    3d0391 <_ZN5MCLoc11RelocWithPFEv+0x1661>
  3d034e:	49 8b 04 24          	mov    (%r12),%rax
  3d0352:	4c 89 e7             	mov    %r12,%rdi
  3d0355:	ff 50 10             	call   *0x10(%rax)
  3d0358:	48 83 3d d0 97 52 00 	cmpq   $0x0,0x5297d0(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d035f:	00 
  3d0360:	74 13                	je     3d0375 <_ZN5MCLoc11RelocWithPFEv+0x1645>
  3d0362:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d0367:	f0 41 0f c1 44 24 0c 	lock xadd %eax,0xc(%r12)
  3d036e:	83 f8 01             	cmp    $0x1,%eax
  3d0371:	74 14                	je     3d0387 <_ZN5MCLoc11RelocWithPFEv+0x1657>
  3d0373:	eb 1c                	jmp    3d0391 <_ZN5MCLoc11RelocWithPFEv+0x1661>
  3d0375:	41 8b 44 24 0c       	mov    0xc(%r12),%eax
  3d037a:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d037d:	41 89 4c 24 0c       	mov    %ecx,0xc(%r12)
  3d0382:	83 f8 01             	cmp    $0x1,%eax
  3d0385:	75 0a                	jne    3d0391 <_ZN5MCLoc11RelocWithPFEv+0x1661>
  3d0387:	49 8b 04 24          	mov    (%r12),%rax
  3d038b:	4c 89 e7             	mov    %r12,%rdi
  3d038e:	ff 50 18             	call   *0x18(%rax)
  3d0391:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d0396:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d039b:	48 39 c7             	cmp    %rax,%rdi
  3d039e:	74 05                	je     3d03a5 <_ZN5MCLoc11RelocWithPFEv+0x1675>
  3d03a0:	e8 4b f5 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d03a5:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3d03ac:	00 
  3d03ad:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3d03b4:	00 
  3d03b5:	48 39 c7             	cmp    %rax,%rdi
  3d03b8:	4c 8b b4 24 e8 00 00 	mov    0xe8(%rsp),%r14
  3d03bf:	00 
  3d03c0:	4c 8d bc 24 50 01 00 	lea    0x150(%rsp),%r15
  3d03c7:	00 
  3d03c8:	74 05                	je     3d03cf <_ZN5MCLoc11RelocWithPFEv+0x169f>
  3d03ca:	e8 21 f5 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d03cf:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3d03d6:	00 
  3d03d7:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d03de:	00 
  3d03df:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d03e3:	48 8b 8c 24 b8 00 00 	mov    0xb8(%rsp),%rcx
  3d03ea:	00 
  3d03eb:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d03f2:	00 
  3d03f3:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  3d03fa:	00 
  3d03fb:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d0402:	00 
  3d0403:	48 8b 84 24 c8 00 00 	mov    0xc8(%rsp),%rax
  3d040a:	00 
  3d040b:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d0412:	00 
  3d0413:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d041a:	00 
  3d041b:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d0422:	00 
  3d0423:	48 39 c7             	cmp    %rax,%rdi
  3d0426:	74 05                	je     3d042d <_ZN5MCLoc11RelocWithPFEv+0x16fd>
  3d0428:	e8 c3 f4 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d042d:	48 8b 84 24 d0 00 00 	mov    0xd0(%rsp),%rax
  3d0434:	00 
  3d0435:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d043c:	00 
  3d043d:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d0444:	00 
  3d0445:	e8 b6 36 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d044a:	48 8b 84 24 d8 00 00 	mov    0xd8(%rsp),%rax
  3d0451:	00 
  3d0452:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d0459:	00 
  3d045a:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d045e:	48 8b 8c 24 e0 00 00 	mov    0xe0(%rsp),%rcx
  3d0465:	00 
  3d0466:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d046d:	00 
  3d046e:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d0475:	00 00 00 00 00 
  3d047a:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d0481:	00 
  3d0482:	e8 39 82 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3d0487:	4c 89 f7             	mov    %r14,%rdi
  3d048a:	e8 f1 1c de ff       	call   1b2180 <_ZN5MCLoc16GetLocLikelihoodEv@plt>
  3d048f:	f2 41 0f 11 86 48 0f 	movsd  %xmm0,0xf48(%r14)
  3d0496:	00 00 
  3d0498:	f2 41 0f 11 86 60 d0 	movsd  %xmm0,0x3d0d060(%r14)
  3d049f:	d0 03 
  3d04a1:	66 41 0f 2e 86 98 d2 	ucomisd 0x3d0d298(%r14),%xmm0
  3d04a8:	d0 03 
  3d04aa:	0f 86 1f 01 00 00    	jbe    3d05cf <_ZN5MCLoc11RelocWithPFEv+0x189f>
  3d04b0:	4c 89 bc 24 40 01 00 	mov    %r15,0x140(%rsp)
  3d04b7:	00 
  3d04b8:	48 b8 75 63 63 65 73 	movabs $0x6465737365636375,%rax
  3d04bf:	73 65 64 
  3d04c2:	48 89 84 24 56 01 00 	mov    %rax,0x156(%rsp)
  3d04c9:	00 
  3d04ca:	48 b8 72 65 6c 6f 63 	movabs $0x637553636f6c6572,%rax
  3d04d1:	53 75 63 
  3d04d4:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d04db:	00 
  3d04dc:	48 c7 84 24 48 01 00 	movq   $0xe,0x148(%rsp)
  3d04e3:	00 0e 00 00 00 
  3d04e8:	c6 84 24 5e 01 00 00 	movb   $0x0,0x15e(%rsp)
  3d04ef:	00 
  3d04f0:	48 8d b4 24 40 01 00 	lea    0x140(%rsp),%rsi
  3d04f7:	00 
  3d04f8:	4c 89 f7             	mov    %r14,%rdi
  3d04fb:	e8 00 8b de ff       	call   1b9000 <_ZN5MCLoc9FireEventERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE@plt>
  3d0500:	48 8b bc 24 40 01 00 	mov    0x140(%rsp),%rdi
  3d0507:	00 
  3d0508:	4c 39 ff             	cmp    %r15,%rdi
  3d050b:	74 05                	je     3d0512 <_ZN5MCLoc11RelocWithPFEv+0x17e2>
  3d050d:	e8 de f3 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d0512:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  3d0519:	00 
  3d051a:	be 18 00 00 00       	mov    $0x18,%esi
  3d051f:	e8 ec 48 de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3d0524:	48 8d bc 24 50 01 00 	lea    0x150(%rsp),%rdi
  3d052b:	00 
  3d052c:	48 8d 35 15 10 1a 00 	lea    0x1a1015(%rip),%rsi        # 571548 <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc9FireEventERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEE4$_80JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x3ba8>
  3d0533:	ba 0e 00 00 00       	mov    $0xe,%edx
  3d0538:	e8 b3 05 de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3d053d:	48 8d b4 24 58 01 00 	lea    0x158(%rsp),%rsi
  3d0544:	00 
  3d0545:	48 8d bc 24 90 00 00 	lea    0x90(%rsp),%rdi
  3d054c:	00 
  3d054d:	e8 0e 47 de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3d0552:	e8 89 73 de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3d0557:	49 89 c7             	mov    %rax,%r15
  3d055a:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3d055f:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3d0564:	4c 8b ac 24 90 00 00 	mov    0x90(%rsp),%r13
  3d056b:	00 
  3d056c:	4c 8b a4 24 98 00 00 	mov    0x98(%rsp),%r12
  3d0573:	00 
  3d0574:	4d 85 ed             	test   %r13,%r13
  3d0577:	75 09                	jne    3d0582 <_ZN5MCLoc11RelocWithPFEv+0x1852>
  3d0579:	4d 85 e4             	test   %r12,%r12
  3d057c:	0f 85 bf 16 00 00    	jne    3d1c41 <_ZN5MCLoc11RelocWithPFEv+0x2f11>
  3d0582:	49 89 ce             	mov    %rcx,%r14
  3d0585:	49 83 fc 10          	cmp    $0x10,%r12
  3d0589:	72 25                	jb     3d05b0 <_ZN5MCLoc11RelocWithPFEv+0x1880>
  3d058b:	4d 85 e4             	test   %r12,%r12
  3d058e:	0f 88 c5 16 00 00    	js     3d1c59 <_ZN5MCLoc11RelocWithPFEv+0x2f29>
  3d0594:	49 8d 7c 24 01       	lea    0x1(%r12),%rdi
  3d0599:	e8 c2 6c de ff       	call   1b7260 <_Znwm@plt>
  3d059e:	49 89 c6             	mov    %rax,%r14
  3d05a1:	4c 89 74 24 08       	mov    %r14,0x8(%rsp)
  3d05a6:	4c 89 64 24 18       	mov    %r12,0x18(%rsp)
  3d05ab:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3d05b0:	4d 85 e4             	test   %r12,%r12
  3d05b3:	0f 84 39 01 00 00    	je     3d06f2 <_ZN5MCLoc11RelocWithPFEv+0x19c2>
  3d05b9:	49 83 fc 01          	cmp    $0x1,%r12
  3d05bd:	0f 85 1c 01 00 00    	jne    3d06df <_ZN5MCLoc11RelocWithPFEv+0x19af>
  3d05c3:	41 8a 45 00          	mov    0x0(%r13),%al
  3d05c7:	41 88 06             	mov    %al,(%r14)
  3d05ca:	e9 23 01 00 00       	jmp    3d06f2 <_ZN5MCLoc11RelocWithPFEv+0x19c2>
  3d05cf:	4c 89 bc 24 40 01 00 	mov    %r15,0x140(%rsp)
  3d05d6:	00 
  3d05d7:	48 b8 72 65 6c 6f 63 	movabs $0x696146636f6c6572,%rax
  3d05de:	46 61 69 
  3d05e1:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d05e8:	00 
  3d05e9:	c7 84 24 58 01 00 00 	movl   $0x64656c,0x158(%rsp)
  3d05f0:	6c 65 64 00 
  3d05f4:	48 c7 84 24 48 01 00 	movq   $0xb,0x148(%rsp)
  3d05fb:	00 0b 00 00 00 
  3d0600:	48 8d b4 24 40 01 00 	lea    0x140(%rsp),%rsi
  3d0607:	00 
  3d0608:	4c 89 f7             	mov    %r14,%rdi
  3d060b:	e8 f0 89 de ff       	call   1b9000 <_ZN5MCLoc9FireEventERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE@plt>
  3d0610:	48 8b bc 24 40 01 00 	mov    0x140(%rsp),%rdi
  3d0617:	00 
  3d0618:	4c 39 ff             	cmp    %r15,%rdi
  3d061b:	74 05                	je     3d0622 <_ZN5MCLoc11RelocWithPFEv+0x18f2>
  3d061d:	e8 ce f2 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d0622:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  3d0629:	00 
  3d062a:	be 18 00 00 00       	mov    $0x18,%esi
  3d062f:	e8 dc 47 de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3d0634:	48 8d bc 24 50 01 00 	lea    0x150(%rsp),%rdi
  3d063b:	00 
  3d063c:	48 8d 35 53 07 1a 00 	lea    0x1a0753(%rip),%rsi        # 570d96 <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc9FireEventERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEE4$_80JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x33f6>
  3d0643:	ba 0b 00 00 00       	mov    $0xb,%edx
  3d0648:	e8 a3 04 de ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3d064d:	48 8d b4 24 58 01 00 	lea    0x158(%rsp),%rsi
  3d0654:	00 
  3d0655:	48 8d bc 24 90 00 00 	lea    0x90(%rsp),%rdi
  3d065c:	00 
  3d065d:	e8 fe 45 de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3d0662:	e8 79 72 de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3d0667:	49 89 c7             	mov    %rax,%r15
  3d066a:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3d066f:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3d0674:	4c 8b ac 24 90 00 00 	mov    0x90(%rsp),%r13
  3d067b:	00 
  3d067c:	4c 8b a4 24 98 00 00 	mov    0x98(%rsp),%r12
  3d0683:	00 
  3d0684:	4d 85 ed             	test   %r13,%r13
  3d0687:	75 09                	jne    3d0692 <_ZN5MCLoc11RelocWithPFEv+0x1962>
  3d0689:	4d 85 e4             	test   %r12,%r12
  3d068c:	0f 85 bb 15 00 00    	jne    3d1c4d <_ZN5MCLoc11RelocWithPFEv+0x2f1d>
  3d0692:	49 89 ce             	mov    %rcx,%r14
  3d0695:	49 83 fc 10          	cmp    $0x10,%r12
  3d0699:	72 25                	jb     3d06c0 <_ZN5MCLoc11RelocWithPFEv+0x1990>
  3d069b:	4d 85 e4             	test   %r12,%r12
  3d069e:	0f 88 c1 15 00 00    	js     3d1c65 <_ZN5MCLoc11RelocWithPFEv+0x2f35>
  3d06a4:	49 8d 7c 24 01       	lea    0x1(%r12),%rdi
  3d06a9:	e8 b2 6b de ff       	call   1b7260 <_Znwm@plt>
  3d06ae:	49 89 c6             	mov    %rax,%r14
  3d06b1:	4c 89 74 24 08       	mov    %r14,0x8(%rsp)
  3d06b6:	4c 89 64 24 18       	mov    %r12,0x18(%rsp)
  3d06bb:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3d06c0:	4d 85 e4             	test   %r12,%r12
  3d06c3:	0f 84 8f 01 00 00    	je     3d0858 <_ZN5MCLoc11RelocWithPFEv+0x1b28>
  3d06c9:	49 83 fc 01          	cmp    $0x1,%r12
  3d06cd:	0f 85 72 01 00 00    	jne    3d0845 <_ZN5MCLoc11RelocWithPFEv+0x1b15>
  3d06d3:	41 8a 45 00          	mov    0x0(%r13),%al
  3d06d7:	41 88 06             	mov    %al,(%r14)
  3d06da:	e9 79 01 00 00       	jmp    3d0858 <_ZN5MCLoc11RelocWithPFEv+0x1b28>
  3d06df:	4c 89 f7             	mov    %r14,%rdi
  3d06e2:	4c 89 ee             	mov    %r13,%rsi
  3d06e5:	4c 89 e2             	mov    %r12,%rdx
  3d06e8:	e8 93 68 de ff       	call   1b6f80 <memcpy@plt>
  3d06ed:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3d06f2:	4c 89 64 24 10       	mov    %r12,0x10(%rsp)
  3d06f7:	43 c6 04 26 00       	movb   $0x0,(%r14,%r12,1)
  3d06fc:	4c 8d ac 24 00 01 00 	lea    0x100(%rsp),%r13
  3d0703:	00 
  3d0704:	4c 89 ac 24 f0 00 00 	mov    %r13,0xf0(%rsp)
  3d070b:	00 
  3d070c:	4c 8b 64 24 08       	mov    0x8(%rsp),%r12
  3d0711:	49 39 cc             	cmp    %rcx,%r12
  3d0714:	74 17                	je     3d072d <_ZN5MCLoc11RelocWithPFEv+0x19fd>
  3d0716:	4c 89 a4 24 f0 00 00 	mov    %r12,0xf0(%rsp)
  3d071d:	00 
  3d071e:	48 8b 44 24 18       	mov    0x18(%rsp),%rax
  3d0723:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  3d072a:	00 
  3d072b:	eb 0d                	jmp    3d073a <_ZN5MCLoc11RelocWithPFEv+0x1a0a>
  3d072d:	66 0f 10 01          	movupd (%rcx),%xmm0
  3d0731:	66 41 0f 11 45 00    	movupd %xmm0,0x0(%r13)
  3d0737:	4d 89 ec             	mov    %r13,%r12
  3d073a:	4c 8b 74 24 10       	mov    0x10(%rsp),%r14
  3d073f:	4c 89 b4 24 f8 00 00 	mov    %r14,0xf8(%rsp)
  3d0746:	00 
  3d0747:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3d074c:	48 c7 44 24 10 00 00 	movq   $0x0,0x10(%rsp)
  3d0753:	00 00 
  3d0755:	c6 44 24 18 00       	movb   $0x0,0x18(%rsp)
  3d075a:	48 c7 44 24 78 00 00 	movq   $0x0,0x78(%rsp)
  3d0761:	00 00 
  3d0763:	bf 28 00 00 00       	mov    $0x28,%edi
  3d0768:	e8 f3 6a de ff       	call   1b7260 <_Znwm@plt>
  3d076d:	48 89 c1             	mov    %rax,%rcx
  3d0770:	48 83 c1 10          	add    $0x10,%rcx
  3d0774:	48 89 08             	mov    %rcx,(%rax)
  3d0777:	4d 39 ec             	cmp    %r13,%r12
  3d077a:	74 11                	je     3d078d <_ZN5MCLoc11RelocWithPFEv+0x1a5d>
  3d077c:	4c 89 20             	mov    %r12,(%rax)
  3d077f:	48 8b 8c 24 00 01 00 	mov    0x100(%rsp),%rcx
  3d0786:	00 
  3d0787:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3d078b:	eb 0a                	jmp    3d0797 <_ZN5MCLoc11RelocWithPFEv+0x1a67>
  3d078d:	66 41 0f 10 45 00    	movupd 0x0(%r13),%xmm0
  3d0793:	66 0f 11 01          	movupd %xmm0,(%rcx)
  3d0797:	4c 89 ac 24 f0 00 00 	mov    %r13,0xf0(%rsp)
  3d079e:	00 
  3d079f:	48 c7 84 24 f8 00 00 	movq   $0x0,0xf8(%rsp)
  3d07a6:	00 00 00 00 00 
  3d07ab:	c6 84 24 00 01 00 00 	movb   $0x0,0x100(%rsp)
  3d07b2:	00 
  3d07b3:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3d07b7:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3d07bc:	48 8d 05 8d 08 01 00 	lea    0x1088d(%rip),%rax        # 3e1050 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc11RelocWithPFEvE4$_12vEEE9_M_invokeERKSt9_Any_data>
  3d07c3:	48 89 84 24 80 00 00 	mov    %rax,0x80(%rsp)
  3d07ca:	00 
  3d07cb:	48 8d 05 5e 0a 01 00 	lea    0x10a5e(%rip),%rax        # 3e1230 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc11RelocWithPFEvE4$_12vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3d07d2:	48 89 44 24 78       	mov    %rax,0x78(%rsp)
  3d07d7:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3d07de:	00 00 
  3d07e0:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3d07e5:	48 8d 54 24 28       	lea    0x28(%rsp),%rdx
  3d07ea:	48 8d 4c 24 68       	lea    0x68(%rsp),%rcx
  3d07ef:	31 f6                	xor    %esi,%esi
  3d07f1:	e8 9a 34 de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3d07f6:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3d07fb:	48 85 ff             	test   %rdi,%rdi
  3d07fe:	74 17                	je     3d0817 <_ZN5MCLoc11RelocWithPFEv+0x1ae7>
  3d0800:	48 8b 07             	mov    (%rdi),%rax
  3d0803:	48 8b 35 c6 91 52 00 	mov    0x5291c6(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3d080a:	ff 50 20             	call   *0x20(%rax)
  3d080d:	49 89 c5             	mov    %rax,%r13
  3d0810:	4c 8b 64 24 50       	mov    0x50(%rsp),%r12
  3d0815:	eb 06                	jmp    3d081d <_ZN5MCLoc11RelocWithPFEv+0x1aed>
  3d0817:	45 31 e4             	xor    %r12d,%r12d
  3d081a:	45 31 ed             	xor    %r13d,%r13d
  3d081d:	4c 89 6c 24 48       	mov    %r13,0x48(%rsp)
  3d0822:	4d 85 e4             	test   %r12,%r12
  3d0825:	0f 84 86 01 00 00    	je     3d09b1 <_ZN5MCLoc11RelocWithPFEv+0x1c81>
  3d082b:	48 83 3d fd 92 52 00 	cmpq   $0x0,0x5292fd(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d0832:	00 
  3d0833:	0f 84 72 01 00 00    	je     3d09ab <_ZN5MCLoc11RelocWithPFEv+0x1c7b>
  3d0839:	f0 41 83 44 24 08 01 	lock addl $0x1,0x8(%r12)
  3d0840:	e9 6c 01 00 00       	jmp    3d09b1 <_ZN5MCLoc11RelocWithPFEv+0x1c81>
  3d0845:	4c 89 f7             	mov    %r14,%rdi
  3d0848:	4c 89 ee             	mov    %r13,%rsi
  3d084b:	4c 89 e2             	mov    %r12,%rdx
  3d084e:	e8 2d 67 de ff       	call   1b6f80 <memcpy@plt>
  3d0853:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3d0858:	4c 89 64 24 10       	mov    %r12,0x10(%rsp)
  3d085d:	43 c6 04 26 00       	movb   $0x0,(%r14,%r12,1)
  3d0862:	4c 8d ac 24 00 01 00 	lea    0x100(%rsp),%r13
  3d0869:	00 
  3d086a:	4c 89 ac 24 f0 00 00 	mov    %r13,0xf0(%rsp)
  3d0871:	00 
  3d0872:	4c 8b 64 24 08       	mov    0x8(%rsp),%r12
  3d0877:	49 39 cc             	cmp    %rcx,%r12
  3d087a:	74 17                	je     3d0893 <_ZN5MCLoc11RelocWithPFEv+0x1b63>
  3d087c:	4c 89 a4 24 f0 00 00 	mov    %r12,0xf0(%rsp)
  3d0883:	00 
  3d0884:	48 8b 44 24 18       	mov    0x18(%rsp),%rax
  3d0889:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  3d0890:	00 
  3d0891:	eb 0d                	jmp    3d08a0 <_ZN5MCLoc11RelocWithPFEv+0x1b70>
  3d0893:	66 0f 10 01          	movupd (%rcx),%xmm0
  3d0897:	66 41 0f 11 45 00    	movupd %xmm0,0x0(%r13)
  3d089d:	4d 89 ec             	mov    %r13,%r12
  3d08a0:	4c 8b 74 24 10       	mov    0x10(%rsp),%r14
  3d08a5:	4c 89 b4 24 f8 00 00 	mov    %r14,0xf8(%rsp)
  3d08ac:	00 
  3d08ad:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3d08b2:	48 c7 44 24 10 00 00 	movq   $0x0,0x10(%rsp)
  3d08b9:	00 00 
  3d08bb:	c6 44 24 18 00       	movb   $0x0,0x18(%rsp)
  3d08c0:	48 c7 44 24 78 00 00 	movq   $0x0,0x78(%rsp)
  3d08c7:	00 00 
  3d08c9:	bf 28 00 00 00       	mov    $0x28,%edi
  3d08ce:	e8 8d 69 de ff       	call   1b7260 <_Znwm@plt>
  3d08d3:	48 89 c1             	mov    %rax,%rcx
  3d08d6:	48 83 c1 10          	add    $0x10,%rcx
  3d08da:	48 89 08             	mov    %rcx,(%rax)
  3d08dd:	4d 39 ec             	cmp    %r13,%r12
  3d08e0:	74 11                	je     3d08f3 <_ZN5MCLoc11RelocWithPFEv+0x1bc3>
  3d08e2:	4c 89 20             	mov    %r12,(%rax)
  3d08e5:	48 8b 8c 24 00 01 00 	mov    0x100(%rsp),%rcx
  3d08ec:	00 
  3d08ed:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3d08f1:	eb 0a                	jmp    3d08fd <_ZN5MCLoc11RelocWithPFEv+0x1bcd>
  3d08f3:	66 41 0f 10 45 00    	movupd 0x0(%r13),%xmm0
  3d08f9:	66 0f 11 01          	movupd %xmm0,(%rcx)
  3d08fd:	4c 89 ac 24 f0 00 00 	mov    %r13,0xf0(%rsp)
  3d0904:	00 
  3d0905:	48 c7 84 24 f8 00 00 	movq   $0x0,0xf8(%rsp)
  3d090c:	00 00 00 00 00 
  3d0911:	c6 84 24 00 01 00 00 	movb   $0x0,0x100(%rsp)
  3d0918:	00 
  3d0919:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3d091d:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3d0922:	48 8d 05 87 0b 01 00 	lea    0x10b87(%rip),%rax        # 3e14b0 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc11RelocWithPFEvE4$_13vEEE9_M_invokeERKSt9_Any_data>
  3d0929:	48 89 84 24 80 00 00 	mov    %rax,0x80(%rsp)
  3d0930:	00 
  3d0931:	48 8d 05 58 0d 01 00 	lea    0x10d58(%rip),%rax        # 3e1690 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc11RelocWithPFEvE4$_13vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3d0938:	48 89 44 24 78       	mov    %rax,0x78(%rsp)
  3d093d:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3d0944:	00 00 
  3d0946:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3d094b:	48 8d 54 24 28       	lea    0x28(%rsp),%rdx
  3d0950:	48 8d 4c 24 68       	lea    0x68(%rsp),%rcx
  3d0955:	31 f6                	xor    %esi,%esi
  3d0957:	e8 34 33 de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3d095c:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3d0961:	48 85 ff             	test   %rdi,%rdi
  3d0964:	74 17                	je     3d097d <_ZN5MCLoc11RelocWithPFEv+0x1c4d>
  3d0966:	48 8b 07             	mov    (%rdi),%rax
  3d0969:	48 8b 35 60 90 52 00 	mov    0x529060(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3d0970:	ff 50 20             	call   *0x20(%rax)
  3d0973:	49 89 c5             	mov    %rax,%r13
  3d0976:	4c 8b 64 24 50       	mov    0x50(%rsp),%r12
  3d097b:	eb 06                	jmp    3d0983 <_ZN5MCLoc11RelocWithPFEv+0x1c53>
  3d097d:	45 31 e4             	xor    %r12d,%r12d
  3d0980:	45 31 ed             	xor    %r13d,%r13d
  3d0983:	4c 89 6c 24 48       	mov    %r13,0x48(%rsp)
  3d0988:	4d 85 e4             	test   %r12,%r12
  3d098b:	0f 84 e2 00 00 00    	je     3d0a73 <_ZN5MCLoc11RelocWithPFEv+0x1d43>
  3d0991:	48 83 3d 97 91 52 00 	cmpq   $0x0,0x529197(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d0998:	00 
  3d0999:	0f 84 ce 00 00 00    	je     3d0a6d <_ZN5MCLoc11RelocWithPFEv+0x1d3d>
  3d099f:	f0 41 83 44 24 08 01 	lock addl $0x1,0x8(%r12)
  3d09a6:	e9 c8 00 00 00       	jmp    3d0a73 <_ZN5MCLoc11RelocWithPFEv+0x1d43>
  3d09ab:	41 83 44 24 08 01    	addl   $0x1,0x8(%r12)
  3d09b1:	48 c7 44 24 38 00 00 	movq   $0x0,0x38(%rsp)
  3d09b8:	00 00 
  3d09ba:	bf 10 00 00 00       	mov    $0x10,%edi
  3d09bf:	e8 9c 68 de ff       	call   1b7260 <_Znwm@plt>
  3d09c4:	4c 89 28             	mov    %r13,(%rax)
  3d09c7:	4c 89 60 08          	mov    %r12,0x8(%rax)
  3d09cb:	48 89 44 24 28       	mov    %rax,0x28(%rsp)
  3d09d0:	48 8d 05 89 09 01 00 	lea    0x10989(%rip),%rax        # 3e1360 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_12JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3d09d7:	48 89 44 24 40       	mov    %rax,0x40(%rsp)
  3d09dc:	48 8d 05 ad 09 01 00 	lea    0x109ad(%rip),%rax        # 3e1390 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_12JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3d09e3:	48 89 44 24 38       	mov    %rax,0x38(%rsp)
  3d09e8:	49 8d 7f 08          	lea    0x8(%r15),%rdi
  3d09ec:	48 8d 74 24 28       	lea    0x28(%rsp),%rsi
  3d09f1:	e8 0a 14 de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3d09f6:	49 81 c7 c0 01 00 00 	add    $0x1c0,%r15
  3d09fd:	4c 89 ff             	mov    %r15,%rdi
  3d0a00:	e8 6b 77 de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3d0a05:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3d0a0a:	48 8d bc 24 88 03 00 	lea    0x388(%rsp),%rdi
  3d0a11:	00 
  3d0a12:	e8 b9 86 de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3d0a17:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3d0a1c:	48 85 c0             	test   %rax,%rax
  3d0a1f:	4c 8b a4 24 e8 00 00 	mov    0xe8(%rsp),%r12
  3d0a26:	00 
  3d0a27:	74 0f                	je     3d0a38 <_ZN5MCLoc11RelocWithPFEv+0x1d08>
  3d0a29:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3d0a2e:	ba 03 00 00 00       	mov    $0x3,%edx
  3d0a33:	48 89 fe             	mov    %rdi,%rsi
  3d0a36:	ff d0                	call   *%rax
  3d0a38:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3d0a3d:	4d 85 ff             	test   %r15,%r15
  3d0a40:	0f 84 29 01 00 00    	je     3d0b6f <_ZN5MCLoc11RelocWithPFEv+0x1e3f>
  3d0a46:	48 83 3d e2 90 52 00 	cmpq   $0x0,0x5290e2(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d0a4d:	00 
  3d0a4e:	0f 84 db 00 00 00    	je     3d0b2f <_ZN5MCLoc11RelocWithPFEv+0x1dff>
  3d0a54:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d0a59:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d0a5f:	83 f8 01             	cmp    $0x1,%eax
  3d0a62:	0f 84 d7 00 00 00    	je     3d0b3f <_ZN5MCLoc11RelocWithPFEv+0x1e0f>
  3d0a68:	e9 02 01 00 00       	jmp    3d0b6f <_ZN5MCLoc11RelocWithPFEv+0x1e3f>
  3d0a6d:	41 83 44 24 08 01    	addl   $0x1,0x8(%r12)
  3d0a73:	48 c7 44 24 38 00 00 	movq   $0x0,0x38(%rsp)
  3d0a7a:	00 00 
  3d0a7c:	bf 10 00 00 00       	mov    $0x10,%edi
  3d0a81:	e8 da 67 de ff       	call   1b7260 <_Znwm@plt>
  3d0a86:	4c 89 28             	mov    %r13,(%rax)
  3d0a89:	4c 89 60 08          	mov    %r12,0x8(%rax)
  3d0a8d:	48 89 44 24 28       	mov    %rax,0x28(%rsp)
  3d0a92:	48 8d 05 27 0d 01 00 	lea    0x10d27(%rip),%rax        # 3e17c0 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_13JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3d0a99:	48 89 44 24 40       	mov    %rax,0x40(%rsp)
  3d0a9e:	48 8d 05 4b 0d 01 00 	lea    0x10d4b(%rip),%rax        # 3e17f0 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_13JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3d0aa5:	48 89 44 24 38       	mov    %rax,0x38(%rsp)
  3d0aaa:	49 8d 7f 08          	lea    0x8(%r15),%rdi
  3d0aae:	48 8d 74 24 28       	lea    0x28(%rsp),%rsi
  3d0ab3:	e8 48 13 de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3d0ab8:	49 81 c7 c0 01 00 00 	add    $0x1c0,%r15
  3d0abf:	4c 89 ff             	mov    %r15,%rdi
  3d0ac2:	e8 a9 76 de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3d0ac7:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3d0acc:	48 8d bc 24 78 03 00 	lea    0x378(%rsp),%rdi
  3d0ad3:	00 
  3d0ad4:	e8 f7 85 de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3d0ad9:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3d0ade:	48 85 c0             	test   %rax,%rax
  3d0ae1:	4c 8b a4 24 e8 00 00 	mov    0xe8(%rsp),%r12
  3d0ae8:	00 
  3d0ae9:	74 0f                	je     3d0afa <_ZN5MCLoc11RelocWithPFEv+0x1dca>
  3d0aeb:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3d0af0:	ba 03 00 00 00       	mov    $0x3,%edx
  3d0af5:	48 89 fe             	mov    %rdi,%rsi
  3d0af8:	ff d0                	call   *%rax
  3d0afa:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3d0aff:	4d 85 ff             	test   %r15,%r15
  3d0b02:	0f 84 f8 00 00 00    	je     3d0c00 <_ZN5MCLoc11RelocWithPFEv+0x1ed0>
  3d0b08:	48 83 3d 20 90 52 00 	cmpq   $0x0,0x529020(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d0b0f:	00 
  3d0b10:	0f 84 aa 00 00 00    	je     3d0bc0 <_ZN5MCLoc11RelocWithPFEv+0x1e90>
  3d0b16:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d0b1b:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d0b21:	83 f8 01             	cmp    $0x1,%eax
  3d0b24:	0f 84 a6 00 00 00    	je     3d0bd0 <_ZN5MCLoc11RelocWithPFEv+0x1ea0>
  3d0b2a:	e9 d1 00 00 00       	jmp    3d0c00 <_ZN5MCLoc11RelocWithPFEv+0x1ed0>
  3d0b2f:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d0b33:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d0b36:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d0b3a:	83 f8 01             	cmp    $0x1,%eax
  3d0b3d:	75 30                	jne    3d0b6f <_ZN5MCLoc11RelocWithPFEv+0x1e3f>
  3d0b3f:	49 8b 07             	mov    (%r15),%rax
  3d0b42:	4c 89 ff             	mov    %r15,%rdi
  3d0b45:	ff 50 10             	call   *0x10(%rax)
  3d0b48:	48 83 3d e0 8f 52 00 	cmpq   $0x0,0x528fe0(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d0b4f:	00 
  3d0b50:	0f 84 6b 07 00 00    	je     3d12c1 <_ZN5MCLoc11RelocWithPFEv+0x2591>
  3d0b56:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d0b5b:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d0b61:	83 f8 01             	cmp    $0x1,%eax
  3d0b64:	75 09                	jne    3d0b6f <_ZN5MCLoc11RelocWithPFEv+0x1e3f>
  3d0b66:	49 8b 07             	mov    (%r15),%rax
  3d0b69:	4c 89 ff             	mov    %r15,%rdi
  3d0b6c:	ff 50 18             	call   *0x18(%rax)
  3d0b6f:	48 8b 44 24 78       	mov    0x78(%rsp),%rax
  3d0b74:	48 85 c0             	test   %rax,%rax
  3d0b77:	74 0f                	je     3d0b88 <_ZN5MCLoc11RelocWithPFEv+0x1e58>
  3d0b79:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3d0b7e:	ba 03 00 00 00       	mov    $0x3,%edx
  3d0b83:	48 89 fe             	mov    %rdi,%rsi
  3d0b86:	ff d0                	call   *%rax
  3d0b88:	4c 8b bc 24 90 03 00 	mov    0x390(%rsp),%r15
  3d0b8f:	00 
  3d0b90:	4d 85 ff             	test   %r15,%r15
  3d0b93:	0f 84 f8 00 00 00    	je     3d0c91 <_ZN5MCLoc11RelocWithPFEv+0x1f61>
  3d0b99:	48 83 3d 8f 8f 52 00 	cmpq   $0x0,0x528f8f(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d0ba0:	00 
  3d0ba1:	0f 84 aa 00 00 00    	je     3d0c51 <_ZN5MCLoc11RelocWithPFEv+0x1f21>
  3d0ba7:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d0bac:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d0bb2:	83 f8 01             	cmp    $0x1,%eax
  3d0bb5:	0f 84 a6 00 00 00    	je     3d0c61 <_ZN5MCLoc11RelocWithPFEv+0x1f31>
  3d0bbb:	e9 d1 00 00 00       	jmp    3d0c91 <_ZN5MCLoc11RelocWithPFEv+0x1f61>
  3d0bc0:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d0bc4:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d0bc7:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d0bcb:	83 f8 01             	cmp    $0x1,%eax
  3d0bce:	75 30                	jne    3d0c00 <_ZN5MCLoc11RelocWithPFEv+0x1ed0>
  3d0bd0:	49 8b 07             	mov    (%r15),%rax
  3d0bd3:	4c 89 ff             	mov    %r15,%rdi
  3d0bd6:	ff 50 10             	call   *0x10(%rax)
  3d0bd9:	48 83 3d 4f 8f 52 00 	cmpq   $0x0,0x528f4f(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d0be0:	00 
  3d0be1:	0f 84 f3 06 00 00    	je     3d12da <_ZN5MCLoc11RelocWithPFEv+0x25aa>
  3d0be7:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d0bec:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d0bf2:	83 f8 01             	cmp    $0x1,%eax
  3d0bf5:	75 09                	jne    3d0c00 <_ZN5MCLoc11RelocWithPFEv+0x1ed0>
  3d0bf7:	49 8b 07             	mov    (%r15),%rax
  3d0bfa:	4c 89 ff             	mov    %r15,%rdi
  3d0bfd:	ff 50 18             	call   *0x18(%rax)
  3d0c00:	48 8b 44 24 78       	mov    0x78(%rsp),%rax
  3d0c05:	48 85 c0             	test   %rax,%rax
  3d0c08:	74 0f                	je     3d0c19 <_ZN5MCLoc11RelocWithPFEv+0x1ee9>
  3d0c0a:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3d0c0f:	ba 03 00 00 00       	mov    $0x3,%edx
  3d0c14:	48 89 fe             	mov    %rdi,%rsi
  3d0c17:	ff d0                	call   *%rax
  3d0c19:	4c 8b bc 24 80 03 00 	mov    0x380(%rsp),%r15
  3d0c20:	00 
  3d0c21:	4d 85 ff             	test   %r15,%r15
  3d0c24:	0f 84 8d 01 00 00    	je     3d0db7 <_ZN5MCLoc11RelocWithPFEv+0x2087>
  3d0c2a:	48 83 3d fe 8e 52 00 	cmpq   $0x0,0x528efe(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d0c31:	00 
  3d0c32:	0f 84 3f 01 00 00    	je     3d0d77 <_ZN5MCLoc11RelocWithPFEv+0x2047>
  3d0c38:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d0c3d:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d0c43:	83 f8 01             	cmp    $0x1,%eax
  3d0c46:	0f 84 3b 01 00 00    	je     3d0d87 <_ZN5MCLoc11RelocWithPFEv+0x2057>
  3d0c4c:	e9 66 01 00 00       	jmp    3d0db7 <_ZN5MCLoc11RelocWithPFEv+0x2087>
  3d0c51:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d0c55:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d0c58:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d0c5c:	83 f8 01             	cmp    $0x1,%eax
  3d0c5f:	75 30                	jne    3d0c91 <_ZN5MCLoc11RelocWithPFEv+0x1f61>
  3d0c61:	49 8b 07             	mov    (%r15),%rax
  3d0c64:	4c 89 ff             	mov    %r15,%rdi
  3d0c67:	ff 50 10             	call   *0x10(%rax)
  3d0c6a:	48 83 3d be 8e 52 00 	cmpq   $0x0,0x528ebe(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d0c71:	00 
  3d0c72:	0f 84 7b 06 00 00    	je     3d12f3 <_ZN5MCLoc11RelocWithPFEv+0x25c3>
  3d0c78:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d0c7d:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d0c83:	83 f8 01             	cmp    $0x1,%eax
  3d0c86:	75 09                	jne    3d0c91 <_ZN5MCLoc11RelocWithPFEv+0x1f61>
  3d0c88:	49 8b 07             	mov    (%r15),%rax
  3d0c8b:	4c 89 ff             	mov    %r15,%rdi
  3d0c8e:	ff 50 18             	call   *0x18(%rax)
  3d0c91:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d0c96:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d0c9b:	48 39 c7             	cmp    %rax,%rdi
  3d0c9e:	74 05                	je     3d0ca5 <_ZN5MCLoc11RelocWithPFEv+0x1f75>
  3d0ca0:	e8 4b ec dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d0ca5:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3d0cac:	00 
  3d0cad:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3d0cb4:	00 
  3d0cb5:	48 39 c7             	cmp    %rax,%rdi
  3d0cb8:	74 05                	je     3d0cbf <_ZN5MCLoc11RelocWithPFEv+0x1f8f>
  3d0cba:	e8 31 ec dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d0cbf:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3d0cc6:	00 
  3d0cc7:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d0cce:	00 
  3d0ccf:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d0cd3:	48 8b 8c 24 b8 00 00 	mov    0xb8(%rsp),%rcx
  3d0cda:	00 
  3d0cdb:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d0ce2:	00 
  3d0ce3:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  3d0cea:	00 
  3d0ceb:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d0cf2:	00 
  3d0cf3:	48 8b 84 24 c8 00 00 	mov    0xc8(%rsp),%rax
  3d0cfa:	00 
  3d0cfb:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d0d02:	00 
  3d0d03:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d0d0a:	00 
  3d0d0b:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d0d12:	00 
  3d0d13:	48 39 c7             	cmp    %rax,%rdi
  3d0d16:	74 05                	je     3d0d1d <_ZN5MCLoc11RelocWithPFEv+0x1fed>
  3d0d18:	e8 d3 eb dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d0d1d:	48 8b 84 24 d0 00 00 	mov    0xd0(%rsp),%rax
  3d0d24:	00 
  3d0d25:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d0d2c:	00 
  3d0d2d:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d0d34:	00 
  3d0d35:	e8 c6 2d de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d0d3a:	48 8b 84 24 d8 00 00 	mov    0xd8(%rsp),%rax
  3d0d41:	00 
  3d0d42:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d0d49:	00 
  3d0d4a:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d0d4e:	48 8b 8c 24 e0 00 00 	mov    0xe0(%rsp),%rcx
  3d0d55:	00 
  3d0d56:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d0d5d:	00 
  3d0d5e:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d0d65:	00 00 00 00 00 
  3d0d6a:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d0d71:	00 
  3d0d72:	e9 21 01 00 00       	jmp    3d0e98 <_ZN5MCLoc11RelocWithPFEv+0x2168>
  3d0d77:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d0d7b:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d0d7e:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d0d82:	83 f8 01             	cmp    $0x1,%eax
  3d0d85:	75 30                	jne    3d0db7 <_ZN5MCLoc11RelocWithPFEv+0x2087>
  3d0d87:	49 8b 07             	mov    (%r15),%rax
  3d0d8a:	4c 89 ff             	mov    %r15,%rdi
  3d0d8d:	ff 50 10             	call   *0x10(%rax)
  3d0d90:	48 83 3d 98 8d 52 00 	cmpq   $0x0,0x528d98(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d0d97:	00 
  3d0d98:	0f 84 6e 05 00 00    	je     3d130c <_ZN5MCLoc11RelocWithPFEv+0x25dc>
  3d0d9e:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d0da3:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d0da9:	83 f8 01             	cmp    $0x1,%eax
  3d0dac:	75 09                	jne    3d0db7 <_ZN5MCLoc11RelocWithPFEv+0x2087>
  3d0dae:	49 8b 07             	mov    (%r15),%rax
  3d0db1:	4c 89 ff             	mov    %r15,%rdi
  3d0db4:	ff 50 18             	call   *0x18(%rax)
  3d0db7:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d0dbc:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d0dc1:	48 39 c7             	cmp    %rax,%rdi
  3d0dc4:	74 05                	je     3d0dcb <_ZN5MCLoc11RelocWithPFEv+0x209b>
  3d0dc6:	e8 25 eb dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d0dcb:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3d0dd2:	00 
  3d0dd3:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3d0dda:	00 
  3d0ddb:	48 39 c7             	cmp    %rax,%rdi
  3d0dde:	74 05                	je     3d0de5 <_ZN5MCLoc11RelocWithPFEv+0x20b5>
  3d0de0:	e8 0b eb dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d0de5:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3d0dec:	00 
  3d0ded:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d0df4:	00 
  3d0df5:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d0df9:	48 8b 8c 24 b8 00 00 	mov    0xb8(%rsp),%rcx
  3d0e00:	00 
  3d0e01:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d0e08:	00 
  3d0e09:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  3d0e10:	00 
  3d0e11:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d0e18:	00 
  3d0e19:	48 8b 84 24 c8 00 00 	mov    0xc8(%rsp),%rax
  3d0e20:	00 
  3d0e21:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d0e28:	00 
  3d0e29:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d0e30:	00 
  3d0e31:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d0e38:	00 
  3d0e39:	48 39 c7             	cmp    %rax,%rdi
  3d0e3c:	74 05                	je     3d0e43 <_ZN5MCLoc11RelocWithPFEv+0x2113>
  3d0e3e:	e8 ad ea dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d0e43:	48 8b 84 24 d0 00 00 	mov    0xd0(%rsp),%rax
  3d0e4a:	00 
  3d0e4b:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d0e52:	00 
  3d0e53:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d0e5a:	00 
  3d0e5b:	e8 a0 2c de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d0e60:	48 8b 84 24 d8 00 00 	mov    0xd8(%rsp),%rax
  3d0e67:	00 
  3d0e68:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d0e6f:	00 
  3d0e70:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d0e74:	48 8b 8c 24 e0 00 00 	mov    0xe0(%rsp),%rcx
  3d0e7b:	00 
  3d0e7c:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d0e83:	00 
  3d0e84:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d0e8b:	00 00 00 00 00 
  3d0e90:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d0e97:	00 
  3d0e98:	e8 23 78 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3d0e9d:	41 8b 84 24 88 d3 d0 	mov    0x3d0d388(%r12),%eax
  3d0ea4:	03 
  3d0ea5:	31 c9                	xor    %ecx,%ecx
  3d0ea7:	41 86 8c 24 20 d3 d0 	xchg   %cl,0x3d0d320(%r12)
  3d0eae:	03 
  3d0eaf:	83 f8 01             	cmp    $0x1,%eax
  3d0eb2:	0f 85 dd 06 00 00    	jne    3d1595 <_ZN5MCLoc11RelocWithPFEv+0x2865>
  3d0eb8:	41 8a 84 24 70 d8 d0 	mov    0x3d0d870(%r12),%al
  3d0ebf:	03 
  3d0ec0:	a8 01                	test   $0x1,%al
  3d0ec2:	0f 85 cd 06 00 00    	jne    3d1595 <_ZN5MCLoc11RelocWithPFEv+0x2865>
  3d0ec8:	66 0f 57 c0          	xorpd  %xmm0,%xmm0
  3d0ecc:	66 0f 29 84 24 f0 02 	movapd %xmm0,0x2f0(%rsp)
  3d0ed3:	00 00 
  3d0ed5:	4d 8d bc 24 f0 0e 00 	lea    0xef0(%r12),%r15
  3d0edc:	00 
  3d0edd:	48 c7 84 24 00 03 00 	movq   $0x0,0x300(%rsp)
  3d0ee4:	00 00 00 00 00 
  3d0ee9:	48 83 3d 3f 8c 52 00 	cmpq   $0x0,0x528c3f(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d0ef0:	00 
  3d0ef1:	74 10                	je     3d0f03 <_ZN5MCLoc11RelocWithPFEv+0x21d3>
  3d0ef3:	4c 89 ff             	mov    %r15,%rdi
  3d0ef6:	e8 35 67 de ff       	call   1b7630 <pthread_mutex_lock@plt>
  3d0efb:	85 c0                	test   %eax,%eax
  3d0efd:	0f 85 86 0d 00 00    	jne    3d1c89 <_ZN5MCLoc11RelocWithPFEv+0x2f59>
  3d0f03:	66 41 0f 10 84 24 50 	movupd 0xf50(%r12),%xmm0
  3d0f0a:	0f 00 00 
  3d0f0d:	66 0f 5e 05 eb 1b 19 	divpd  0x191beb(%rip),%xmm0        # 562b00 <_ZTS11errorLogger+0x1b6>
  3d0f14:	00 
  3d0f15:	66 0f 29 84 24 f0 02 	movapd %xmm0,0x2f0(%rsp)
  3d0f1c:	00 00 
  3d0f1e:	f2 41 0f 10 84 24 60 	movsd  0xf60(%r12),%xmm0
  3d0f25:	0f 00 00 
  3d0f28:	f2 0f 11 84 24 08 03 	movsd  %xmm0,0x308(%rsp)
  3d0f2f:	00 00 
  3d0f31:	e8 ea 3f de ff       	call   1b4f20 <sin@plt>
  3d0f36:	66 0f 29 84 24 e0 02 	movapd %xmm0,0x2e0(%rsp)
  3d0f3d:	00 00 
  3d0f3f:	66 0f 14 c0          	unpcklpd %xmm0,%xmm0
  3d0f43:	66 0f 57 c9          	xorpd  %xmm1,%xmm1
  3d0f47:	66 0f 59 c1          	mulpd  %xmm1,%xmm0
  3d0f4b:	66 0f 29 84 24 30 03 	movapd %xmm0,0x330(%rsp)
  3d0f52:	00 00 
  3d0f54:	f2 0f 10 84 24 08 03 	movsd  0x308(%rsp),%xmm0
  3d0f5b:	00 00 
  3d0f5d:	e8 7e 55 de ff       	call   1b64e0 <cos@plt>
  3d0f62:	f2 0f 10 0d 86 f8 18 	movsd  0x18f886(%rip),%xmm1        # 5607f0 <_ZTS30IdentificationToolSmoothOnTime+0x70>
  3d0f69:	00 
  3d0f6a:	f2 0f 5c c8          	subsd  %xmm0,%xmm1
  3d0f6e:	66 0f 28 d1          	movapd %xmm1,%xmm2
  3d0f72:	66 0f 14 d2          	unpcklpd %xmm2,%xmm2
  3d0f76:	66 0f 59 15 e2 f7 18 	mulpd  0x18f7e2(%rip),%xmm2        # 560760 <_fini+0x2c>
  3d0f7d:	00 
  3d0f7e:	66 45 0f 57 c0       	xorpd  %xmm8,%xmm8
  3d0f83:	66 0f 28 e2          	movapd %xmm2,%xmm4
  3d0f87:	f2 41 0f 59 e0       	mulsd  %xmm8,%xmm4
  3d0f8c:	0f 28 9c 24 30 03 00 	movaps 0x330(%rsp),%xmm3
  3d0f93:	00 
  3d0f94:	0f 28 eb             	movaps %xmm3,%xmm5
  3d0f97:	0f 12 ed             	movhlps %xmm5,%xmm5
  3d0f9a:	f2 0f 58 ea          	addsd  %xmm2,%xmm5
  3d0f9e:	f2 0f 11 ac 24 20 01 	movsd  %xmm5,0x120(%rsp)
  3d0fa5:	00 00 
  3d0fa7:	66 0f 28 ea          	movapd %xmm2,%xmm5
  3d0fab:	66 0f 14 ec          	unpcklpd %xmm4,%xmm5
  3d0faf:	0f 28 f3             	movaps %xmm3,%xmm6
  3d0fb2:	66 0f 28 bc 24 e0 02 	movapd 0x2e0(%rsp),%xmm7
  3d0fb9:	00 00 
  3d0fbb:	66 0f c6 f7 01       	shufpd $0x1,%xmm7,%xmm6
  3d0fc0:	66 0f 5c ee          	subpd  %xmm6,%xmm5
  3d0fc4:	66 0f 29 ac 24 00 01 	movapd %xmm5,0x100(%rsp)
  3d0fcb:	00 00 
  3d0fcd:	66 0f 28 ea          	movapd %xmm2,%xmm5
  3d0fd1:	0f 12 ed             	movhlps %xmm5,%xmm5
  3d0fd4:	0f 28 f5             	movaps %xmm5,%xmm6
  3d0fd7:	f2 0f 5c f3          	subsd  %xmm3,%xmm6
  3d0fdb:	f2 0f 11 b4 24 28 01 	movsd  %xmm6,0x128(%rsp)
  3d0fe2:	00 00 
  3d0fe4:	66 0f 28 f0          	movapd %xmm0,%xmm6
  3d0fe8:	f2 0f 58 c8          	addsd  %xmm0,%xmm1
  3d0fec:	66 0f 14 c7          	unpcklpd %xmm7,%xmm0
  3d0ff0:	66 0f 14 e4          	unpcklpd %xmm4,%xmm4
  3d0ff4:	66 0f 58 e0          	addpd  %xmm0,%xmm4
  3d0ff8:	66 0f 29 a4 24 f0 00 	movapd %xmm4,0xf0(%rsp)
  3d0fff:	00 00 
  3d1001:	f2 41 0f 59 e8       	mulsd  %xmm8,%xmm5
  3d1006:	66 0f 14 f3          	unpcklpd %xmm3,%xmm6
  3d100a:	f2 0f 10 d5          	movsd  %xmm5,%xmm2
  3d100e:	66 0f 58 d6          	addpd  %xmm6,%xmm2
  3d1012:	66 0f 29 94 24 10 01 	movapd %xmm2,0x110(%rsp)
  3d1019:	00 00 
  3d101b:	f2 0f 11 8c 24 30 01 	movsd  %xmm1,0x130(%rsp)
  3d1022:	00 00 
  3d1024:	48 83 3d 04 8b 52 00 	cmpq   $0x0,0x528b04(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d102b:	00 
  3d102c:	74 08                	je     3d1036 <_ZN5MCLoc11RelocWithPFEv+0x2306>
  3d102e:	4c 89 ff             	mov    %r15,%rdi
  3d1031:	e8 7a 65 de ff       	call   1b75b0 <pthread_mutex_unlock@plt>
  3d1036:	49 8b bc 24 a0 d8 d0 	mov    0x3d0d8a0(%r12),%rdi
  3d103d:	03 
  3d103e:	48 8d b4 24 f0 02 00 	lea    0x2f0(%rsp),%rsi
  3d1045:	00 
  3d1046:	48 8d 94 24 f0 00 00 	lea    0xf0(%rsp),%rdx
  3d104d:	00 
  3d104e:	e8 8d 39 de ff       	call   1b49e0 <_ZN18esekf_localization14ESEKFLocalizer11SetInitPoseERKN5Eigen6MatrixIdLi3ELi1ELi0ELi3ELi1EEERKNS2_IdLi3ELi3ELi0ELi3ELi3EEE@plt>
  3d1053:	49 8b bc 24 a0 d8 d0 	mov    0x3d0d8a0(%r12),%rdi
  3d105a:	03 
  3d105b:	c7 07 00 00 00 00    	movl   $0x0,(%rdi)
  3d1061:	e8 4a fb dd ff       	call   1b0bb0 <_ZN18esekf_localization14ESEKFLocalizer14ResetExtrinsicEv@plt>
  3d1066:	48 b8 00 00 00 00 00 	movabs $0xbff0000000000000,%rax
  3d106d:	00 f0 bf 
  3d1070:	49 89 84 24 30 d7 d0 	mov    %rax,0x3d0d730(%r12)
  3d1077:	03 
  3d1078:	48 8d 3d e9 5f 52 00 	lea    0x525fe9(%rip),%rdi        # 8f7068 <.got>
  3d107f:	e8 dc 6c de ff       	call   1b7d60 <__tls_get_addr@plt>
  3d1084:	49 89 c6             	mov    %rax,%r14
  3d1087:	8a 80 c8 00 00 00    	mov    0xc8(%rax),%al
  3d108d:	84 c0                	test   %al,%al
  3d108f:	0f 84 13 0b 00 00    	je     3d1ba8 <_ZN5MCLoc11RelocWithPFEv+0x2e78>
  3d1095:	4c 89 f0             	mov    %r14,%rax
  3d1098:	48 8b b0 c0 00 00 00 	mov    0xc0(%rax),%rsi
  3d109f:	48 8d 15 32 34 1f 00 	lea    0x1f3432(%rip),%rdx        # 5c44d8 <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc15SetGnssParticleERKNS_8protocol12Message_GNSSEE4$_43JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x248>
  3d10a6:	48 8d bc 24 38 01 00 	lea    0x138(%rsp),%rdi
  3d10ad:	00 
  3d10ae:	b9 ff ff ff ff       	mov    $0xffffffff,%ecx
  3d10b3:	e8 18 46 de ff       	call   1b56d0 <_ZN8profiler11TextMessageC1EmPKcj@plt>
  3d10b8:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  3d10bf:	00 
  3d10c0:	be 18 00 00 00       	mov    $0x18,%esi
  3d10c5:	e8 46 3d de ff       	call   1b4e10 <_ZNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEC1ESt13_Ios_Openmode@plt>
  3d10ca:	48 8d bc 24 50 01 00 	lea    0x150(%rsp),%rdi
  3d10d1:	00 
  3d10d2:	48 8d 35 16 34 1f 00 	lea    0x1f3416(%rip),%rsi        # 5c44ef <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc15SetGnssParticleERKNS_8protocol12Message_GNSSEE4$_43JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x25f>
  3d10d9:	ba 0b 00 00 00       	mov    $0xb,%edx
  3d10de:	e8 0d fa dd ff       	call   1b0af0 <_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@plt>
  3d10e3:	48 8d b4 24 58 01 00 	lea    0x158(%rsp),%rsi
  3d10ea:	00 
  3d10eb:	48 8d 7c 24 08       	lea    0x8(%rsp),%rdi
  3d10f0:	e8 6b 3b de ff       	call   1b4c60 <_ZNKSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEE3strEv@plt>
  3d10f5:	e8 e6 67 de ff       	call   1b78e0 <_ZN3rbk6Logger6threadEv@plt>
  3d10fa:	49 89 c7             	mov    %rax,%r15
  3d10fd:	48 8d 4c 24 58       	lea    0x58(%rsp),%rcx
  3d1102:	48 89 4c 24 48       	mov    %rcx,0x48(%rsp)
  3d1107:	4c 8b 6c 24 08       	mov    0x8(%rsp),%r13
  3d110c:	4c 8b 64 24 10       	mov    0x10(%rsp),%r12
  3d1111:	4d 85 ed             	test   %r13,%r13
  3d1114:	75 09                	jne    3d111f <_ZN5MCLoc11RelocWithPFEv+0x23ef>
  3d1116:	4d 85 e4             	test   %r12,%r12
  3d1119:	0f 85 52 0b 00 00    	jne    3d1c71 <_ZN5MCLoc11RelocWithPFEv+0x2f41>
  3d111f:	49 89 ce             	mov    %rcx,%r14
  3d1122:	49 83 fc 10          	cmp    $0x10,%r12
  3d1126:	72 25                	jb     3d114d <_ZN5MCLoc11RelocWithPFEv+0x241d>
  3d1128:	4d 85 e4             	test   %r12,%r12
  3d112b:	0f 88 5f 0b 00 00    	js     3d1c90 <_ZN5MCLoc11RelocWithPFEv+0x2f60>
  3d1131:	49 8d 7c 24 01       	lea    0x1(%r12),%rdi
  3d1136:	e8 25 61 de ff       	call   1b7260 <_Znwm@plt>
  3d113b:	49 89 c6             	mov    %rax,%r14
  3d113e:	4c 89 74 24 48       	mov    %r14,0x48(%rsp)
  3d1143:	4c 89 64 24 58       	mov    %r12,0x58(%rsp)
  3d1148:	48 8d 4c 24 58       	lea    0x58(%rsp),%rcx
  3d114d:	4d 85 e4             	test   %r12,%r12
  3d1150:	74 33                	je     3d1185 <_ZN5MCLoc11RelocWithPFEv+0x2455>
  3d1152:	49 83 fc 01          	cmp    $0x1,%r12
  3d1156:	75 09                	jne    3d1161 <_ZN5MCLoc11RelocWithPFEv+0x2431>
  3d1158:	41 8a 45 00          	mov    0x0(%r13),%al
  3d115c:	41 88 06             	mov    %al,(%r14)
  3d115f:	eb 24                	jmp    3d1185 <_ZN5MCLoc11RelocWithPFEv+0x2455>
  3d1161:	4c 89 bc 24 e0 02 00 	mov    %r15,0x2e0(%rsp)
  3d1168:	00 
  3d1169:	49 89 cf             	mov    %rcx,%r15
  3d116c:	4c 89 f7             	mov    %r14,%rdi
  3d116f:	4c 89 ee             	mov    %r13,%rsi
  3d1172:	4c 89 e2             	mov    %r12,%rdx
  3d1175:	e8 06 5e de ff       	call   1b6f80 <memcpy@plt>
  3d117a:	4c 89 f9             	mov    %r15,%rcx
  3d117d:	4c 8b bc 24 e0 02 00 	mov    0x2e0(%rsp),%r15
  3d1184:	00 
  3d1185:	4c 89 64 24 50       	mov    %r12,0x50(%rsp)
  3d118a:	43 c6 04 26 00       	movb   $0x0,(%r14,%r12,1)
  3d118f:	4c 8d 6c 24 78       	lea    0x78(%rsp),%r13
  3d1194:	4c 89 6c 24 68       	mov    %r13,0x68(%rsp)
  3d1199:	4c 8b 64 24 48       	mov    0x48(%rsp),%r12
  3d119e:	49 39 cc             	cmp    %rcx,%r12
  3d11a1:	74 11                	je     3d11b4 <_ZN5MCLoc11RelocWithPFEv+0x2484>
  3d11a3:	4c 89 64 24 68       	mov    %r12,0x68(%rsp)
  3d11a8:	48 8b 44 24 58       	mov    0x58(%rsp),%rax
  3d11ad:	48 89 44 24 78       	mov    %rax,0x78(%rsp)
  3d11b2:	eb 0d                	jmp    3d11c1 <_ZN5MCLoc11RelocWithPFEv+0x2491>
  3d11b4:	66 0f 10 01          	movupd (%rcx),%xmm0
  3d11b8:	66 41 0f 11 45 00    	movupd %xmm0,0x0(%r13)
  3d11be:	4d 89 ec             	mov    %r13,%r12
  3d11c1:	4c 8b 74 24 50       	mov    0x50(%rsp),%r14
  3d11c6:	4c 89 74 24 70       	mov    %r14,0x70(%rsp)
  3d11cb:	48 89 4c 24 48       	mov    %rcx,0x48(%rsp)
  3d11d0:	48 c7 44 24 50 00 00 	movq   $0x0,0x50(%rsp)
  3d11d7:	00 00 
  3d11d9:	c6 44 24 58 00       	movb   $0x0,0x58(%rsp)
  3d11de:	48 c7 44 24 38 00 00 	movq   $0x0,0x38(%rsp)
  3d11e5:	00 00 
  3d11e7:	bf 28 00 00 00       	mov    $0x28,%edi
  3d11ec:	e8 6f 60 de ff       	call   1b7260 <_Znwm@plt>
  3d11f1:	48 89 c1             	mov    %rax,%rcx
  3d11f4:	48 83 c1 10          	add    $0x10,%rcx
  3d11f8:	48 89 08             	mov    %rcx,(%rax)
  3d11fb:	4d 39 ec             	cmp    %r13,%r12
  3d11fe:	74 0e                	je     3d120e <_ZN5MCLoc11RelocWithPFEv+0x24de>
  3d1200:	4c 89 20             	mov    %r12,(%rax)
  3d1203:	48 8b 4c 24 78       	mov    0x78(%rsp),%rcx
  3d1208:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3d120c:	eb 0a                	jmp    3d1218 <_ZN5MCLoc11RelocWithPFEv+0x24e8>
  3d120e:	66 41 0f 10 45 00    	movupd 0x0(%r13),%xmm0
  3d1214:	66 0f 11 01          	movupd %xmm0,(%rcx)
  3d1218:	4c 89 6c 24 68       	mov    %r13,0x68(%rsp)
  3d121d:	48 c7 44 24 70 00 00 	movq   $0x0,0x70(%rsp)
  3d1224:	00 00 
  3d1226:	c6 44 24 78 00       	movb   $0x0,0x78(%rsp)
  3d122b:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3d122f:	48 89 44 24 28       	mov    %rax,0x28(%rsp)
  3d1234:	48 8d 05 d5 06 01 00 	lea    0x106d5(%rip),%rax        # 3e1910 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc11RelocWithPFEvE4$_14vEEE9_M_invokeERKSt9_Any_data>
  3d123b:	48 89 44 24 40       	mov    %rax,0x40(%rsp)
  3d1240:	48 8d 05 a9 08 01 00 	lea    0x108a9(%rip),%rax        # 3e1af0 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc11RelocWithPFEvE4$_14vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3d1247:	48 89 44 24 38       	mov    %rax,0x38(%rsp)
  3d124c:	48 c7 84 24 d0 02 00 	movq   $0x0,0x2d0(%rsp)
  3d1253:	00 00 00 00 00 
  3d1258:	48 8d bc 24 d8 02 00 	lea    0x2d8(%rsp),%rdi
  3d125f:	00 
  3d1260:	48 8d 94 24 90 00 00 	lea    0x90(%rsp),%rdx
  3d1267:	00 
  3d1268:	48 8d 4c 24 28       	lea    0x28(%rsp),%rcx
  3d126d:	31 f6                	xor    %esi,%esi
  3d126f:	e8 1c 2a de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3d1274:	48 8b bc 24 d8 02 00 	mov    0x2d8(%rsp),%rdi
  3d127b:	00 
  3d127c:	48 85 ff             	test   %rdi,%rdi
  3d127f:	74 1a                	je     3d129b <_ZN5MCLoc11RelocWithPFEv+0x256b>
  3d1281:	48 8b 07             	mov    (%rdi),%rax
  3d1284:	48 8b 35 45 87 52 00 	mov    0x528745(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3d128b:	ff 50 20             	call   *0x20(%rax)
  3d128e:	49 89 c5             	mov    %rax,%r13
  3d1291:	4c 8b a4 24 d8 02 00 	mov    0x2d8(%rsp),%r12
  3d1298:	00 
  3d1299:	eb 06                	jmp    3d12a1 <_ZN5MCLoc11RelocWithPFEv+0x2571>
  3d129b:	45 31 e4             	xor    %r12d,%r12d
  3d129e:	45 31 ed             	xor    %r13d,%r13d
  3d12a1:	4c 89 ac 24 d0 02 00 	mov    %r13,0x2d0(%rsp)
  3d12a8:	00 
  3d12a9:	4d 85 e4             	test   %r12,%r12
  3d12ac:	74 7d                	je     3d132b <_ZN5MCLoc11RelocWithPFEv+0x25fb>
  3d12ae:	48 83 3d 7a 88 52 00 	cmpq   $0x0,0x52887a(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d12b5:	00 
  3d12b6:	74 6d                	je     3d1325 <_ZN5MCLoc11RelocWithPFEv+0x25f5>
  3d12b8:	f0 41 83 44 24 08 01 	lock addl $0x1,0x8(%r12)
  3d12bf:	eb 6a                	jmp    3d132b <_ZN5MCLoc11RelocWithPFEv+0x25fb>
  3d12c1:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d12c5:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d12c8:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d12cc:	83 f8 01             	cmp    $0x1,%eax
  3d12cf:	0f 85 9a f8 ff ff    	jne    3d0b6f <_ZN5MCLoc11RelocWithPFEv+0x1e3f>
  3d12d5:	e9 8c f8 ff ff       	jmp    3d0b66 <_ZN5MCLoc11RelocWithPFEv+0x1e36>
  3d12da:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d12de:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d12e1:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d12e5:	83 f8 01             	cmp    $0x1,%eax
  3d12e8:	0f 85 12 f9 ff ff    	jne    3d0c00 <_ZN5MCLoc11RelocWithPFEv+0x1ed0>
  3d12ee:	e9 04 f9 ff ff       	jmp    3d0bf7 <_ZN5MCLoc11RelocWithPFEv+0x1ec7>
  3d12f3:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d12f7:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d12fa:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d12fe:	83 f8 01             	cmp    $0x1,%eax
  3d1301:	0f 85 8a f9 ff ff    	jne    3d0c91 <_ZN5MCLoc11RelocWithPFEv+0x1f61>
  3d1307:	e9 7c f9 ff ff       	jmp    3d0c88 <_ZN5MCLoc11RelocWithPFEv+0x1f58>
  3d130c:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d1310:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d1313:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d1317:	83 f8 01             	cmp    $0x1,%eax
  3d131a:	0f 85 97 fa ff ff    	jne    3d0db7 <_ZN5MCLoc11RelocWithPFEv+0x2087>
  3d1320:	e9 89 fa ff ff       	jmp    3d0dae <_ZN5MCLoc11RelocWithPFEv+0x207e>
  3d1325:	41 83 44 24 08 01    	addl   $0x1,0x8(%r12)
  3d132b:	48 c7 84 24 a0 00 00 	movq   $0x0,0xa0(%rsp)
  3d1332:	00 00 00 00 00 
  3d1337:	bf 10 00 00 00       	mov    $0x10,%edi
  3d133c:	e8 1f 5f de ff       	call   1b7260 <_Znwm@plt>
  3d1341:	4c 89 28             	mov    %r13,(%rax)
  3d1344:	4c 89 60 08          	mov    %r12,0x8(%rax)
  3d1348:	48 89 84 24 90 00 00 	mov    %rax,0x90(%rsp)
  3d134f:	00 
  3d1350:	48 8d 05 c9 08 01 00 	lea    0x108c9(%rip),%rax        # 3e1c20 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_14JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3d1357:	48 89 84 24 a8 00 00 	mov    %rax,0xa8(%rsp)
  3d135e:	00 
  3d135f:	48 8d 05 ea 08 01 00 	lea    0x108ea(%rip),%rax        # 3e1c50 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_14JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3d1366:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  3d136d:	00 
  3d136e:	49 8d 7f 08          	lea    0x8(%r15),%rdi
  3d1372:	48 8d b4 24 90 00 00 	lea    0x90(%rsp),%rsi
  3d1379:	00 
  3d137a:	e8 81 0a de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3d137f:	49 81 c7 c0 01 00 00 	add    $0x1c0,%r15
  3d1386:	4c 89 ff             	mov    %r15,%rdi
  3d1389:	e8 e2 6d de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3d138e:	48 8b b4 24 d0 02 00 	mov    0x2d0(%rsp),%rsi
  3d1395:	00 
  3d1396:	48 8d bc 24 68 03 00 	lea    0x368(%rsp),%rdi
  3d139d:	00 
  3d139e:	e8 2d 7d de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3d13a3:	48 8b 84 24 a0 00 00 	mov    0xa0(%rsp),%rax
  3d13aa:	00 
  3d13ab:	48 85 c0             	test   %rax,%rax
  3d13ae:	4c 8b a4 24 e8 00 00 	mov    0xe8(%rsp),%r12
  3d13b5:	00 
  3d13b6:	74 12                	je     3d13ca <_ZN5MCLoc11RelocWithPFEv+0x269a>
  3d13b8:	48 8d bc 24 90 00 00 	lea    0x90(%rsp),%rdi
  3d13bf:	00 
  3d13c0:	ba 03 00 00 00       	mov    $0x3,%edx
  3d13c5:	48 89 fe             	mov    %rdi,%rsi
  3d13c8:	ff d0                	call   *%rax
  3d13ca:	4c 8b bc 24 d8 02 00 	mov    0x2d8(%rsp),%r15
  3d13d1:	00 
  3d13d2:	4d 85 ff             	test   %r15,%r15
  3d13d5:	74 5c                	je     3d1433 <_ZN5MCLoc11RelocWithPFEv+0x2703>
  3d13d7:	48 83 3d 51 87 52 00 	cmpq   $0x0,0x528751(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d13de:	00 
  3d13df:	74 12                	je     3d13f3 <_ZN5MCLoc11RelocWithPFEv+0x26c3>
  3d13e1:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d13e6:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d13ec:	83 f8 01             	cmp    $0x1,%eax
  3d13ef:	74 12                	je     3d1403 <_ZN5MCLoc11RelocWithPFEv+0x26d3>
  3d13f1:	eb 40                	jmp    3d1433 <_ZN5MCLoc11RelocWithPFEv+0x2703>
  3d13f3:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d13f7:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d13fa:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d13fe:	83 f8 01             	cmp    $0x1,%eax
  3d1401:	75 30                	jne    3d1433 <_ZN5MCLoc11RelocWithPFEv+0x2703>
  3d1403:	49 8b 07             	mov    (%r15),%rax
  3d1406:	4c 89 ff             	mov    %r15,%rdi
  3d1409:	ff 50 10             	call   *0x10(%rax)
  3d140c:	48 83 3d 1c 87 52 00 	cmpq   $0x0,0x52871c(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d1413:	00 
  3d1414:	0f 84 f1 06 00 00    	je     3d1b0b <_ZN5MCLoc11RelocWithPFEv+0x2ddb>
  3d141a:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d141f:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d1425:	83 f8 01             	cmp    $0x1,%eax
  3d1428:	75 09                	jne    3d1433 <_ZN5MCLoc11RelocWithPFEv+0x2703>
  3d142a:	49 8b 07             	mov    (%r15),%rax
  3d142d:	4c 89 ff             	mov    %r15,%rdi
  3d1430:	ff 50 18             	call   *0x18(%rax)
  3d1433:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3d1438:	48 85 c0             	test   %rax,%rax
  3d143b:	74 0f                	je     3d144c <_ZN5MCLoc11RelocWithPFEv+0x271c>
  3d143d:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3d1442:	ba 03 00 00 00       	mov    $0x3,%edx
  3d1447:	48 89 fe             	mov    %rdi,%rsi
  3d144a:	ff d0                	call   *%rax
  3d144c:	4c 8b bc 24 70 03 00 	mov    0x370(%rsp),%r15
  3d1453:	00 
  3d1454:	4d 85 ff             	test   %r15,%r15
  3d1457:	74 5c                	je     3d14b5 <_ZN5MCLoc11RelocWithPFEv+0x2785>
  3d1459:	48 83 3d cf 86 52 00 	cmpq   $0x0,0x5286cf(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d1460:	00 
  3d1461:	74 12                	je     3d1475 <_ZN5MCLoc11RelocWithPFEv+0x2745>
  3d1463:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d1468:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d146e:	83 f8 01             	cmp    $0x1,%eax
  3d1471:	74 12                	je     3d1485 <_ZN5MCLoc11RelocWithPFEv+0x2755>
  3d1473:	eb 40                	jmp    3d14b5 <_ZN5MCLoc11RelocWithPFEv+0x2785>
  3d1475:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d1479:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d147c:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d1480:	83 f8 01             	cmp    $0x1,%eax
  3d1483:	75 30                	jne    3d14b5 <_ZN5MCLoc11RelocWithPFEv+0x2785>
  3d1485:	49 8b 07             	mov    (%r15),%rax
  3d1488:	4c 89 ff             	mov    %r15,%rdi
  3d148b:	ff 50 10             	call   *0x10(%rax)
  3d148e:	48 83 3d 9a 86 52 00 	cmpq   $0x0,0x52869a(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d1495:	00 
  3d1496:	0f 84 88 06 00 00    	je     3d1b24 <_ZN5MCLoc11RelocWithPFEv+0x2df4>
  3d149c:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d14a1:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d14a7:	83 f8 01             	cmp    $0x1,%eax
  3d14aa:	75 09                	jne    3d14b5 <_ZN5MCLoc11RelocWithPFEv+0x2785>
  3d14ac:	49 8b 07             	mov    (%r15),%rax
  3d14af:	4c 89 ff             	mov    %r15,%rdi
  3d14b2:	ff 50 18             	call   *0x18(%rax)
  3d14b5:	48 8b 7c 24 48       	mov    0x48(%rsp),%rdi
  3d14ba:	48 8d 44 24 58       	lea    0x58(%rsp),%rax
  3d14bf:	48 39 c7             	cmp    %rax,%rdi
  3d14c2:	74 05                	je     3d14c9 <_ZN5MCLoc11RelocWithPFEv+0x2799>
  3d14c4:	e8 27 e4 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d14c9:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d14ce:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d14d3:	48 39 c7             	cmp    %rax,%rdi
  3d14d6:	74 05                	je     3d14dd <_ZN5MCLoc11RelocWithPFEv+0x27ad>
  3d14d8:	e8 13 e4 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d14dd:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3d14e4:	00 
  3d14e5:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d14ec:	00 
  3d14ed:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d14f1:	48 8b 8c 24 b8 00 00 	mov    0xb8(%rsp),%rcx
  3d14f8:	00 
  3d14f9:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d1500:	00 
  3d1501:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  3d1508:	00 
  3d1509:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d1510:	00 
  3d1511:	48 8b 84 24 c8 00 00 	mov    0xc8(%rsp),%rax
  3d1518:	00 
  3d1519:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d1520:	00 
  3d1521:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d1528:	00 
  3d1529:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d1530:	00 
  3d1531:	48 39 c7             	cmp    %rax,%rdi
  3d1534:	74 05                	je     3d153b <_ZN5MCLoc11RelocWithPFEv+0x280b>
  3d1536:	e8 b5 e3 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d153b:	48 8b 84 24 d0 00 00 	mov    0xd0(%rsp),%rax
  3d1542:	00 
  3d1543:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d154a:	00 
  3d154b:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d1552:	00 
  3d1553:	e8 a8 25 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d1558:	48 8b 84 24 d8 00 00 	mov    0xd8(%rsp),%rax
  3d155f:	00 
  3d1560:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d1567:	00 
  3d1568:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d156c:	48 8b 8c 24 e0 00 00 	mov    0xe0(%rsp),%rcx
  3d1573:	00 
  3d1574:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d157b:	00 
  3d157c:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d1583:	00 00 00 00 00 
  3d1588:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d158f:	00 
  3d1590:	e8 2b 71 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3d1595:	f2 41 0f 10 84 24 50 	movsd  0xf50(%r12),%xmm0
  3d159c:	0f 00 00 
  3d159f:	f2 41 0f 10 8c 24 58 	movsd  0xf58(%r12),%xmm1
  3d15a6:	0f 00 00 
  3d15a9:	f2 0f 10 15 e7 13 19 	movsd  0x1913e7(%rip),%xmm2        # 562998 <_ZTS11errorLogger+0x4e>
  3d15b0:	00 
  3d15b1:	f2 0f 5e c2          	divsd  %xmm2,%xmm0
  3d15b5:	f2 0f 5e ca          	divsd  %xmm2,%xmm1
  3d15b9:	f2 41 0f 10 94 24 60 	movsd  0xf60(%r12),%xmm2
  3d15c0:	0f 00 00 
  3d15c3:	48 8d 15 31 2f 1f 00 	lea    0x1f2f31(%rip),%rdx        # 5c44fb <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc15SetGnssParticleERKNS_8protocol12Message_GNSSEE4$_43JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x26b>
  3d15ca:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  3d15d1:	00 
  3d15d2:	be 80 00 00 00       	mov    $0x80,%esi
  3d15d7:	b0 03                	mov    $0x3,%al
  3d15d9:	e8 92 11 de ff       	call   1b2770 <snprintf@plt>
  3d15de:	48 8d 3d 83 5a 52 00 	lea    0x525a83(%rip),%rdi        # 8f7068 <.got>
  3d15e5:	e8 76 67 de ff       	call   1b7d60 <__tls_get_addr@plt>
  3d15ea:	49 89 c6             	mov    %rax,%r14
  3d15ed:	8a 80 d8 00 00 00    	mov    0xd8(%rax),%al
  3d15f3:	84 c0                	test   %al,%al
  3d15f5:	0f 84 74 05 00 00    	je     3d1b6f <_ZN5MCLoc11RelocWithPFEv+0x2e3f>
  3d15fb:	4c 89 f0             	mov    %r14,%rax
  3d15fe:	48 8b b0 d0 00 00 00 	mov    0xd0(%rax),%rsi
  3d1605:	48 8d bc 24 f0 00 00 	lea    0xf0(%rsp),%rdi
  3d160c:	00 
  3d160d:	48 8d 94 24 40 01 00 	lea    0x140(%rsp),%rdx
  3d1614:	00 
  3d1615:	b9 ff cc 00 ff       	mov    $0xff00ccff,%ecx
  3d161a:	e8 b1 40 de ff       	call   1b56d0 <_ZN8profiler11TextMessageC1EmPKcj@plt>
  3d161f:	41 c7 84 24 5c 18 00 	movl   $0x2,0x185c(%r12)
  3d1626:	00 02 00 00 00 
  3d162b:	41 c6 84 24 67 18 00 	movb   $0x0,0x1867(%r12)
  3d1632:	00 00 
  3d1634:	41 c6 84 24 18 0f 00 	movb   $0x1,0xf18(%r12)
  3d163b:	00 01 
  3d163d:	31 c0                	xor    %eax,%eax
  3d163f:	41 86 84 24 70 d8 d0 	xchg   %al,0x3d0d870(%r12)
  3d1646:	03 
  3d1647:	66 0f 1f 84 00 00 00 	nopw   0x0(%rax,%rax,1)
  3d164e:	00 00 
  3d1650:	48 89 df             	mov    %rbx,%rdi
  3d1653:	e8 58 5f de ff       	call   1b75b0 <pthread_mutex_unlock@plt>
  3d1658:	83 f8 04             	cmp    $0x4,%eax
  3d165b:	74 f3                	je     3d1650 <_ZN5MCLoc11RelocWithPFEv+0x2920>
  3d165d:	48 8d 65 d8          	lea    -0x28(%rbp),%rsp
  3d1661:	5b                   	pop    %rbx
  3d1662:	41 5c                	pop    %r12
  3d1664:	41 5d                	pop    %r13
  3d1666:	41 5e                	pop    %r14
  3d1668:	41 5f                	pop    %r15
  3d166a:	5d                   	pop    %rbp
  3d166b:	c3                   	ret    
  3d166c:	4c 89 f7             	mov    %r14,%rdi
  3d166f:	4c 89 ee             	mov    %r13,%rsi
  3d1672:	4c 89 fa             	mov    %r15,%rdx
  3d1675:	e8 06 59 de ff       	call   1b6f80 <memcpy@plt>
  3d167a:	48 8d 4c 24 18       	lea    0x18(%rsp),%rcx
  3d167f:	4c 89 7c 24 10       	mov    %r15,0x10(%rsp)
  3d1684:	43 c6 04 3e 00       	movb   $0x0,(%r14,%r15,1)
  3d1689:	4c 8d ac 24 00 01 00 	lea    0x100(%rsp),%r13
  3d1690:	00 
  3d1691:	4c 89 ac 24 f0 00 00 	mov    %r13,0xf0(%rsp)
  3d1698:	00 
  3d1699:	4c 8b 7c 24 08       	mov    0x8(%rsp),%r15
  3d169e:	49 39 cf             	cmp    %rcx,%r15
  3d16a1:	74 17                	je     3d16ba <_ZN5MCLoc11RelocWithPFEv+0x298a>
  3d16a3:	4c 89 bc 24 f0 00 00 	mov    %r15,0xf0(%rsp)
  3d16aa:	00 
  3d16ab:	48 8b 44 24 18       	mov    0x18(%rsp),%rax
  3d16b0:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  3d16b7:	00 
  3d16b8:	eb 0d                	jmp    3d16c7 <_ZN5MCLoc11RelocWithPFEv+0x2997>
  3d16ba:	66 0f 10 01          	movupd (%rcx),%xmm0
  3d16be:	66 41 0f 11 45 00    	movupd %xmm0,0x0(%r13)
  3d16c4:	4d 89 ef             	mov    %r13,%r15
  3d16c7:	4c 8b 74 24 10       	mov    0x10(%rsp),%r14
  3d16cc:	4c 89 b4 24 f8 00 00 	mov    %r14,0xf8(%rsp)
  3d16d3:	00 
  3d16d4:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  3d16d9:	48 c7 44 24 10 00 00 	movq   $0x0,0x10(%rsp)
  3d16e0:	00 00 
  3d16e2:	c6 44 24 18 00       	movb   $0x0,0x18(%rsp)
  3d16e7:	48 c7 44 24 78 00 00 	movq   $0x0,0x78(%rsp)
  3d16ee:	00 00 
  3d16f0:	bf 28 00 00 00       	mov    $0x28,%edi
  3d16f5:	e8 66 5b de ff       	call   1b7260 <_Znwm@plt>
  3d16fa:	48 89 c1             	mov    %rax,%rcx
  3d16fd:	48 83 c1 10          	add    $0x10,%rcx
  3d1701:	48 89 08             	mov    %rcx,(%rax)
  3d1704:	4d 39 ef             	cmp    %r13,%r15
  3d1707:	74 11                	je     3d171a <_ZN5MCLoc11RelocWithPFEv+0x29ea>
  3d1709:	4c 89 38             	mov    %r15,(%rax)
  3d170c:	48 8b 8c 24 00 01 00 	mov    0x100(%rsp),%rcx
  3d1713:	00 
  3d1714:	48 89 48 10          	mov    %rcx,0x10(%rax)
  3d1718:	eb 0a                	jmp    3d1724 <_ZN5MCLoc11RelocWithPFEv+0x29f4>
  3d171a:	66 41 0f 10 45 00    	movupd 0x0(%r13),%xmm0
  3d1720:	66 0f 11 01          	movupd %xmm0,(%rcx)
  3d1724:	4c 89 ac 24 f0 00 00 	mov    %r13,0xf0(%rsp)
  3d172b:	00 
  3d172c:	48 c7 84 24 f8 00 00 	movq   $0x0,0xf8(%rsp)
  3d1733:	00 00 00 00 00 
  3d1738:	c6 84 24 00 01 00 00 	movb   $0x0,0x100(%rsp)
  3d173f:	00 
  3d1740:	4c 89 70 08          	mov    %r14,0x8(%rax)
  3d1744:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
  3d1749:	48 8d 05 40 f0 00 00 	lea    0xf040(%rip),%rax        # 3e0790 <_ZNSt17_Function_handlerIFvvESt5_BindIFZN5MCLoc11RelocWithPFEvE4$_10vEEE9_M_invokeERKSt9_Any_data>
  3d1750:	48 89 84 24 80 00 00 	mov    %rax,0x80(%rsp)
  3d1757:	00 
  3d1758:	48 8d 05 11 f2 00 00 	lea    0xf211(%rip),%rax        # 3e0970 <_ZNSt14_Function_base13_Base_managerISt5_BindIFZN5MCLoc11RelocWithPFEvE4$_10vEEE10_M_managerERSt9_Any_dataRKS7_St18_Manager_operation>
  3d175f:	48 89 44 24 78       	mov    %rax,0x78(%rsp)
  3d1764:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  3d176b:	00 00 
  3d176d:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
  3d1772:	48 8d 54 24 28       	lea    0x28(%rsp),%rdx
  3d1777:	48 8d 4c 24 68       	lea    0x68(%rsp),%rcx
  3d177c:	31 f6                	xor    %esi,%esi
  3d177e:	e8 0d 25 de ff       	call   1b3c90 <_ZNSt14__shared_countILN9__gnu_cxx12_Lock_policyE2EEC2ISt13packaged_taskIFvvEESaIS6_EJRSt8functionIS5_EEEESt19_Sp_make_shared_tagPT_RKT0_DpOT1_@plt>
  3d1783:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  3d1788:	48 85 ff             	test   %rdi,%rdi
  3d178b:	74 17                	je     3d17a4 <_ZN5MCLoc11RelocWithPFEv+0x2a74>
  3d178d:	48 8b 07             	mov    (%rdi),%rax
  3d1790:	48 8b 35 39 82 52 00 	mov    0x528239(%rip),%rsi        # 8f99d0 <_ZTISt19_Sp_make_shared_tag@@Base+0x21508>
  3d1797:	ff 50 20             	call   *0x20(%rax)
  3d179a:	49 89 c5             	mov    %rax,%r13
  3d179d:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3d17a2:	eb 06                	jmp    3d17aa <_ZN5MCLoc11RelocWithPFEv+0x2a7a>
  3d17a4:	45 31 ff             	xor    %r15d,%r15d
  3d17a7:	45 31 ed             	xor    %r13d,%r13d
  3d17aa:	4c 89 6c 24 48       	mov    %r13,0x48(%rsp)
  3d17af:	4d 85 ff             	test   %r15,%r15
  3d17b2:	74 17                	je     3d17cb <_ZN5MCLoc11RelocWithPFEv+0x2a9b>
  3d17b4:	48 83 3d 74 83 52 00 	cmpq   $0x0,0x528374(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d17bb:	00 
  3d17bc:	74 08                	je     3d17c6 <_ZN5MCLoc11RelocWithPFEv+0x2a96>
  3d17be:	f0 41 83 47 08 01    	lock addl $0x1,0x8(%r15)
  3d17c4:	eb 05                	jmp    3d17cb <_ZN5MCLoc11RelocWithPFEv+0x2a9b>
  3d17c6:	41 83 47 08 01       	addl   $0x1,0x8(%r15)
  3d17cb:	48 c7 44 24 38 00 00 	movq   $0x0,0x38(%rsp)
  3d17d2:	00 00 
  3d17d4:	bf 10 00 00 00       	mov    $0x10,%edi
  3d17d9:	e8 82 5a de ff       	call   1b7260 <_Znwm@plt>
  3d17de:	4c 89 28             	mov    %r13,(%rax)
  3d17e1:	4c 89 78 08          	mov    %r15,0x8(%rax)
  3d17e5:	48 89 44 24 28       	mov    %rax,0x28(%rsp)
  3d17ea:	48 8d 05 af f2 00 00 	lea    0xf2af(%rip),%rax        # 3e0aa0 <_ZNSt17_Function_handlerIFvvEZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_10JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E9_M_invokeERKSt9_Any_data>
  3d17f1:	48 89 44 24 40       	mov    %rax,0x40(%rsp)
  3d17f6:	48 8d 05 d3 f2 00 00 	lea    0xf2d3(%rip),%rax        # 3e0ad0 <_ZNSt14_Function_base13_Base_managerIZN3rbk6Logger6Thread11move2threadIZN5MCLoc11RelocWithPFEvE4$_10JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_E10_M_managerERSt9_Any_dataRKSH_St18_Manager_operation>
  3d17fd:	48 89 44 24 38       	mov    %rax,0x38(%rsp)
  3d1802:	49 8d 7c 24 08       	lea    0x8(%r12),%rdi
  3d1807:	48 8d 74 24 28       	lea    0x28(%rsp),%rsi
  3d180c:	e8 ef 05 de ff       	call   1b1e00 <_ZN3rbk6Logger6Thread9SafeQueueISt8functionIFvvEEE9push_backERS5_@plt>
  3d1811:	49 81 c4 c0 01 00 00 	add    $0x1c0,%r12
  3d1818:	4c 89 e7             	mov    %r12,%rdi
  3d181b:	e8 50 69 de ff       	call   1b8170 <_ZNSt18condition_variable10notify_oneEv@plt>
  3d1820:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  3d1825:	48 8d bc 24 a8 03 00 	lea    0x3a8(%rsp),%rdi
  3d182c:	00 
  3d182d:	e8 9e 78 de ff       	call   1b90d0 <_ZNSt13packaged_taskIFvvEE10get_futureEv@plt>
  3d1832:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  3d1837:	48 85 c0             	test   %rax,%rax
  3d183a:	74 0f                	je     3d184b <_ZN5MCLoc11RelocWithPFEv+0x2b1b>
  3d183c:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3d1841:	ba 03 00 00 00       	mov    $0x3,%edx
  3d1846:	48 89 fe             	mov    %rdi,%rsi
  3d1849:	ff d0                	call   *%rax
  3d184b:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3d1850:	4d 85 ff             	test   %r15,%r15
  3d1853:	4c 8b b4 24 e8 00 00 	mov    0xe8(%rsp),%r14
  3d185a:	00 
  3d185b:	4c 8b a4 24 e0 02 00 	mov    0x2e0(%rsp),%r12
  3d1862:	00 
  3d1863:	74 5c                	je     3d18c1 <_ZN5MCLoc11RelocWithPFEv+0x2b91>
  3d1865:	48 83 3d c3 82 52 00 	cmpq   $0x0,0x5282c3(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d186c:	00 
  3d186d:	74 12                	je     3d1881 <_ZN5MCLoc11RelocWithPFEv+0x2b51>
  3d186f:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d1874:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d187a:	83 f8 01             	cmp    $0x1,%eax
  3d187d:	74 12                	je     3d1891 <_ZN5MCLoc11RelocWithPFEv+0x2b61>
  3d187f:	eb 40                	jmp    3d18c1 <_ZN5MCLoc11RelocWithPFEv+0x2b91>
  3d1881:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d1885:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d1888:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d188c:	83 f8 01             	cmp    $0x1,%eax
  3d188f:	75 30                	jne    3d18c1 <_ZN5MCLoc11RelocWithPFEv+0x2b91>
  3d1891:	49 8b 07             	mov    (%r15),%rax
  3d1894:	4c 89 ff             	mov    %r15,%rdi
  3d1897:	ff 50 10             	call   *0x10(%rax)
  3d189a:	48 83 3d 8e 82 52 00 	cmpq   $0x0,0x52828e(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d18a1:	00 
  3d18a2:	0f 84 95 02 00 00    	je     3d1b3d <_ZN5MCLoc11RelocWithPFEv+0x2e0d>
  3d18a8:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d18ad:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d18b3:	83 f8 01             	cmp    $0x1,%eax
  3d18b6:	75 09                	jne    3d18c1 <_ZN5MCLoc11RelocWithPFEv+0x2b91>
  3d18b8:	49 8b 07             	mov    (%r15),%rax
  3d18bb:	4c 89 ff             	mov    %r15,%rdi
  3d18be:	ff 50 18             	call   *0x18(%rax)
  3d18c1:	48 8b 44 24 78       	mov    0x78(%rsp),%rax
  3d18c6:	48 85 c0             	test   %rax,%rax
  3d18c9:	74 0f                	je     3d18da <_ZN5MCLoc11RelocWithPFEv+0x2baa>
  3d18cb:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3d18d0:	ba 03 00 00 00       	mov    $0x3,%edx
  3d18d5:	48 89 fe             	mov    %rdi,%rsi
  3d18d8:	ff d0                	call   *%rax
  3d18da:	4c 8b bc 24 b0 03 00 	mov    0x3b0(%rsp),%r15
  3d18e1:	00 
  3d18e2:	4d 85 ff             	test   %r15,%r15
  3d18e5:	74 5c                	je     3d1943 <_ZN5MCLoc11RelocWithPFEv+0x2c13>
  3d18e7:	48 83 3d 41 82 52 00 	cmpq   $0x0,0x528241(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d18ee:	00 
  3d18ef:	74 12                	je     3d1903 <_ZN5MCLoc11RelocWithPFEv+0x2bd3>
  3d18f1:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d18f6:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d18fc:	83 f8 01             	cmp    $0x1,%eax
  3d18ff:	74 12                	je     3d1913 <_ZN5MCLoc11RelocWithPFEv+0x2be3>
  3d1901:	eb 40                	jmp    3d1943 <_ZN5MCLoc11RelocWithPFEv+0x2c13>
  3d1903:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d1907:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d190a:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d190e:	83 f8 01             	cmp    $0x1,%eax
  3d1911:	75 30                	jne    3d1943 <_ZN5MCLoc11RelocWithPFEv+0x2c13>
  3d1913:	49 8b 07             	mov    (%r15),%rax
  3d1916:	4c 89 ff             	mov    %r15,%rdi
  3d1919:	ff 50 10             	call   *0x10(%rax)
  3d191c:	48 83 3d 0c 82 52 00 	cmpq   $0x0,0x52820c(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d1923:	00 
  3d1924:	0f 84 2c 02 00 00    	je     3d1b56 <_ZN5MCLoc11RelocWithPFEv+0x2e26>
  3d192a:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d192f:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d1935:	83 f8 01             	cmp    $0x1,%eax
  3d1938:	75 09                	jne    3d1943 <_ZN5MCLoc11RelocWithPFEv+0x2c13>
  3d193a:	49 8b 07             	mov    (%r15),%rax
  3d193d:	4c 89 ff             	mov    %r15,%rdi
  3d1940:	ff 50 18             	call   *0x18(%rax)
  3d1943:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d1948:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d194d:	48 39 c7             	cmp    %rax,%rdi
  3d1950:	74 05                	je     3d1957 <_ZN5MCLoc11RelocWithPFEv+0x2c27>
  3d1952:	e8 99 df dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d1957:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3d195e:	00 
  3d195f:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3d1966:	00 
  3d1967:	48 39 c7             	cmp    %rax,%rdi
  3d196a:	74 05                	je     3d1971 <_ZN5MCLoc11RelocWithPFEv+0x2c41>
  3d196c:	e8 7f df dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d1971:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3d1978:	00 
  3d1979:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d1980:	00 
  3d1981:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d1985:	48 8b 8c 24 b8 00 00 	mov    0xb8(%rsp),%rcx
  3d198c:	00 
  3d198d:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d1994:	00 
  3d1995:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  3d199c:	00 
  3d199d:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d19a4:	00 
  3d19a5:	48 8b 84 24 c8 00 00 	mov    0xc8(%rsp),%rax
  3d19ac:	00 
  3d19ad:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d19b4:	00 
  3d19b5:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d19bc:	00 
  3d19bd:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d19c4:	00 
  3d19c5:	48 39 c7             	cmp    %rax,%rdi
  3d19c8:	74 05                	je     3d19cf <_ZN5MCLoc11RelocWithPFEv+0x2c9f>
  3d19ca:	e8 21 df dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d19cf:	48 8b 84 24 d0 00 00 	mov    0xd0(%rsp),%rax
  3d19d6:	00 
  3d19d7:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d19de:	00 
  3d19df:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d19e6:	00 
  3d19e7:	e8 14 21 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d19ec:	48 8b 84 24 d8 00 00 	mov    0xd8(%rsp),%rax
  3d19f3:	00 
  3d19f4:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d19fb:	00 
  3d19fc:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d1a00:	48 8b 8c 24 e0 00 00 	mov    0xe0(%rsp),%rcx
  3d1a07:	00 
  3d1a08:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d1a0f:	00 
  3d1a10:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d1a17:	00 00 00 00 00 
  3d1a1c:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d1a23:	00 
  3d1a24:	e8 97 6c de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3d1a29:	4c 89 f7             	mov    %r14,%rdi
  3d1a2c:	4c 89 e6             	mov    %r12,%rsi
  3d1a2f:	e8 1c 1b de ff       	call   1b3550 <_ZN5MCLoc25DoRelocNormalUpdateActionERN3rbk9algorithm10StateVar2DE@plt>
  3d1a34:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  3d1a3b:	00 
  3d1a3c:	e8 cf 60 de ff       	call   1b7b10 <_ZN3rbk9algorithm13MCLParticle2DC1Ev@plt>
  3d1a41:	f2 41 0f 10 86 50 0f 	movsd  0xf50(%r14),%xmm0
  3d1a48:	00 00 
  3d1a4a:	f2 41 0f 10 8e 58 0f 	movsd  0xf58(%r14),%xmm1
  3d1a51:	00 00 
  3d1a53:	f2 41 0f 10 96 60 0f 	movsd  0xf60(%r14),%xmm2
  3d1a5a:	00 00 
  3d1a5c:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  3d1a63:	00 
  3d1a64:	e8 37 f2 dd ff       	call   1b0ca0 <_ZN3rbk9algorithm13MCLParticle2D16setParticleValueEddd@plt>
  3d1a69:	49 8d be 68 d0 d0 03 	lea    0x3d0d068(%r14),%rdi
  3d1a70:	66 0f 57 c0          	xorpd  %xmm0,%xmm0
  3d1a74:	66 0f 29 84 24 10 03 	movapd %xmm0,0x310(%rsp)
  3d1a7b:	00 00 
  3d1a7d:	48 c7 84 24 20 03 00 	movq   $0x0,0x320(%rsp)
  3d1a84:	00 00 00 00 00 
  3d1a89:	48 83 ec 30          	sub    $0x30,%rsp
  3d1a8d:	48 8b 84 24 90 01 00 	mov    0x190(%rsp),%rax
  3d1a94:	00 
  3d1a95:	48 89 44 24 20       	mov    %rax,0x20(%rsp)
  3d1a9a:	66 0f 10 84 24 70 01 	movupd 0x170(%rsp),%xmm0
  3d1aa1:	00 00 
  3d1aa3:	66 0f 10 8c 24 80 01 	movupd 0x180(%rsp),%xmm1
  3d1aaa:	00 00 
  3d1aac:	66 0f 11 4c 24 10    	movupd %xmm1,0x10(%rsp)
  3d1ab2:	66 0f 11 04 24       	movupd %xmm0,(%rsp)
  3d1ab7:	48 8d b4 24 40 03 00 	lea    0x340(%rsp),%rsi
  3d1abe:	00 
  3d1abf:	e8 dc fa dd ff       	call   1b15a0 <_ZN3rbk9algorithm16ParticleFilter2D26getRelocParticleLikelihoodENS0_13MCLParticle2DESt6vectorIdSaIdEE@plt>
  3d1ac4:	48 83 c4 30          	add    $0x30,%rsp
  3d1ac8:	f2 41 0f 11 86 48 0f 	movsd  %xmm0,0xf48(%r14)
  3d1acf:	00 00 
  3d1ad1:	48 8b bc 24 10 03 00 	mov    0x310(%rsp),%rdi
  3d1ad8:	00 
  3d1ad9:	48 85 ff             	test   %rdi,%rdi
  3d1adc:	74 0e                	je     3d1aec <_ZN5MCLoc11RelocWithPFEv+0x2dbc>
  3d1ade:	e8 0d de dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d1ae3:	f2 41 0f 10 86 48 0f 	movsd  0xf48(%r14),%xmm0
  3d1aea:	00 00 
  3d1aec:	66 41 0f 2e 86 98 d2 	ucomisd 0x3d0d298(%r14),%xmm0
  3d1af3:	d0 03 
  3d1af5:	0f 86 55 fb ff ff    	jbe    3d1650 <_ZN5MCLoc11RelocWithPFEv+0x2920>
  3d1afb:	41 c7 86 44 0f 00 00 	movl   $0x65,0xf44(%r14)
  3d1b02:	65 00 00 00 
  3d1b06:	e9 45 fb ff ff       	jmp    3d1650 <_ZN5MCLoc11RelocWithPFEv+0x2920>
  3d1b0b:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d1b0f:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d1b12:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d1b16:	83 f8 01             	cmp    $0x1,%eax
  3d1b19:	0f 85 14 f9 ff ff    	jne    3d1433 <_ZN5MCLoc11RelocWithPFEv+0x2703>
  3d1b1f:	e9 06 f9 ff ff       	jmp    3d142a <_ZN5MCLoc11RelocWithPFEv+0x26fa>
  3d1b24:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d1b28:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d1b2b:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d1b2f:	83 f8 01             	cmp    $0x1,%eax
  3d1b32:	0f 85 7d f9 ff ff    	jne    3d14b5 <_ZN5MCLoc11RelocWithPFEv+0x2785>
  3d1b38:	e9 6f f9 ff ff       	jmp    3d14ac <_ZN5MCLoc11RelocWithPFEv+0x277c>
  3d1b3d:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d1b41:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d1b44:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d1b48:	83 f8 01             	cmp    $0x1,%eax
  3d1b4b:	0f 85 70 fd ff ff    	jne    3d18c1 <_ZN5MCLoc11RelocWithPFEv+0x2b91>
  3d1b51:	e9 62 fd ff ff       	jmp    3d18b8 <_ZN5MCLoc11RelocWithPFEv+0x2b88>
  3d1b56:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d1b5a:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d1b5d:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d1b61:	83 f8 01             	cmp    $0x1,%eax
  3d1b64:	0f 85 d9 fd ff ff    	jne    3d1943 <_ZN5MCLoc11RelocWithPFEv+0x2c13>
  3d1b6a:	e9 cb fd ff ff       	jmp    3d193a <_ZN5MCLoc11RelocWithPFEv+0x2c0a>
  3d1b6f:	4c 89 f0             	mov    %r14,%rax
  3d1b72:	48 8d b8 d0 00 00 00 	lea    0xd0(%rax),%rdi
  3d1b79:	48 8d 35 9e 91 1e 00 	lea    0x1e919e(%rip),%rsi        # 5bad1e <_ZTSZN3rbk6Logger6Thread11move2threadIZN17QuadGridSearchMap15getPostProbBaseERKNS_9algorithm10StateVar2DERSt6vectorIdSaIdEEiE5$_125JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x22ae>
  3d1b80:	48 8d 15 45 29 1f 00 	lea    0x1f2945(%rip),%rdx        # 5c44cc <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc15SetGnssParticleERKNS_8protocol12Message_GNSSEE4$_43JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x23c>
  3d1b87:	48 8d 0d d0 28 1f 00 	lea    0x1f28d0(%rip),%rcx        # 5c445e <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc15SetGnssParticleERKNS_8protocol12Message_GNSSEE4$_43JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1ce>
  3d1b8e:	41 b8 3e 01 00 00    	mov    $0x13e,%r8d
  3d1b94:	e8 17 4f de ff       	call   1b6ab0 <_ZN8profiler18SourceLocationDataC1EPKcS2_S2_j@plt>
  3d1b99:	4c 89 f0             	mov    %r14,%rax
  3d1b9c:	c6 80 d8 00 00 00 01 	movb   $0x1,0xd8(%rax)
  3d1ba3:	e9 53 fa ff ff       	jmp    3d15fb <_ZN5MCLoc11RelocWithPFEv+0x28cb>
  3d1ba8:	4c 89 f0             	mov    %r14,%rax
  3d1bab:	48 8d b8 c0 00 00 00 	lea    0xc0(%rax),%rdi
  3d1bb2:	48 8d 35 65 91 1e 00 	lea    0x1e9165(%rip),%rsi        # 5bad1e <_ZTSZN3rbk6Logger6Thread11move2threadIZN17QuadGridSearchMap15getPostProbBaseERKNS_9algorithm10StateVar2DERSt6vectorIdSaIdEEiE5$_125JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x22ae>
  3d1bb9:	48 8d 15 0c 29 1f 00 	lea    0x1f290c(%rip),%rdx        # 5c44cc <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc15SetGnssParticleERKNS_8protocol12Message_GNSSEE4$_43JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x23c>
  3d1bc0:	48 8d 0d 97 28 1f 00 	lea    0x1f2897(%rip),%rcx        # 5c445e <_ZTSZN3rbk6Logger6Thread11move2threadIZN5MCLoc15SetGnssParticleERKNS_8protocol12Message_GNSSEE4$_43JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1ce>
  3d1bc7:	41 b8 36 01 00 00    	mov    $0x136,%r8d
  3d1bcd:	e8 de 4e de ff       	call   1b6ab0 <_ZN8profiler18SourceLocationDataC1EPKcS2_S2_j@plt>
  3d1bd2:	4c 89 f0             	mov    %r14,%rax
  3d1bd5:	c6 80 c8 00 00 00 01 	movb   $0x1,0xc8(%rax)
  3d1bdc:	e9 b4 f4 ff ff       	jmp    3d1095 <_ZN5MCLoc11RelocWithPFEv+0x2365>
  3d1be1:	48 8d 3d 89 fd 18 00 	lea    0x18fd89(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3d1be8:	e8 d3 52 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3d1bed:	48 8d 3d 7d fd 18 00 	lea    0x18fd7d(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3d1bf4:	e8 c7 52 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3d1bf9:	48 8d 3d 71 fd 18 00 	lea    0x18fd71(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3d1c00:	e8 bb 52 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3d1c05:	48 8d 3d 65 fd 18 00 	lea    0x18fd65(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3d1c0c:	e8 af 52 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3d1c11:	48 8d 3d 24 fd 18 00 	lea    0x18fd24(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3d1c18:	e8 63 de dd ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3d1c1d:	48 8d 3d 18 fd 18 00 	lea    0x18fd18(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3d1c24:	e8 57 de dd ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3d1c29:	48 8d 3d 0c fd 18 00 	lea    0x18fd0c(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3d1c30:	e8 4b de dd ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3d1c35:	48 8d 3d 00 fd 18 00 	lea    0x18fd00(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3d1c3c:	e8 3f de dd ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3d1c41:	48 8d 3d 29 fd 18 00 	lea    0x18fd29(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3d1c48:	e8 73 52 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3d1c4d:	48 8d 3d 1d fd 18 00 	lea    0x18fd1d(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3d1c54:	e8 67 52 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3d1c59:	48 8d 3d dc fc 18 00 	lea    0x18fcdc(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3d1c60:	e8 1b de dd ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3d1c65:	48 8d 3d d0 fc 18 00 	lea    0x18fcd0(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3d1c6c:	e8 0f de dd ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3d1c71:	48 8d 3d f9 fc 18 00 	lea    0x18fcf9(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3d1c78:	e8 43 52 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3d1c7d:	48 8d 3d ed fc 18 00 	lea    0x18fced(%rip),%rdi        # 561971 <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x1a1>
  3d1c84:	e8 37 52 de ff       	call   1b6ec0 <_ZSt19__throw_logic_errorPKc@plt>
  3d1c89:	89 c7                	mov    %eax,%edi
  3d1c8b:	e8 90 d7 dd ff       	call   1af420 <_ZSt20__throw_system_errori@plt>
  3d1c90:	48 8d 3d a5 fc 18 00 	lea    0x18fca5(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3d1c97:	e8 e4 dd dd ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3d1c9c:	48 8d 3d 99 fc 18 00 	lea    0x18fc99(%rip),%rdi        # 56193c <_ZTSZN3rbk6Logger6Thread11move2threadIZN14InterpolateLoc15UpdateAllMsgLocERKNS_8protocol20Message_LocalizationEdE3$_4JEEESt6futureIDTclfp_spfp0_EEEOT_DpOT0_EUlvE_+0x16c>
  3d1ca3:	e8 d8 dd dd ff       	call   1afa80 <_ZSt20__throw_length_errorPKc@plt>
  3d1ca8:	e9 65 15 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d1cad:	e9 60 15 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d1cb2:	e9 ed 00 00 00       	jmp    3d1da4 <_ZN5MCLoc11RelocWithPFEv+0x3074>
  3d1cb7:	e9 ac 01 00 00       	jmp    3d1e68 <_ZN5MCLoc11RelocWithPFEv+0x3138>
  3d1cbc:	48 89 c7             	mov    %rax,%rdi
  3d1cbf:	e8 3c 14 df ff       	call   1c3100 <__clang_call_terminate>
  3d1cc4:	48 89 c7             	mov    %rax,%rdi
  3d1cc7:	e8 34 14 df ff       	call   1c3100 <__clang_call_terminate>
  3d1ccc:	48 89 c7             	mov    %rax,%rdi
  3d1ccf:	e8 2c 14 df ff       	call   1c3100 <__clang_call_terminate>
  3d1cd4:	48 89 c7             	mov    %rax,%rdi
  3d1cd7:	e8 24 14 df ff       	call   1c3100 <__clang_call_terminate>
  3d1cdc:	49 89 c6             	mov    %rax,%r14
  3d1cdf:	48 8b bc 24 10 03 00 	mov    0x310(%rsp),%rdi
  3d1ce6:	00 
  3d1ce7:	48 85 ff             	test   %rdi,%rdi
  3d1cea:	0f 84 30 15 00 00    	je     3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d1cf0:	e8 fb db dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d1cf5:	e9 26 15 00 00       	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d1cfa:	49 89 c6             	mov    %rax,%r14
  3d1cfd:	4d 85 ff             	test   %r15,%r15
  3d1d00:	0f 84 cf 01 00 00    	je     3d1ed5 <_ZN5MCLoc11RelocWithPFEv+0x31a5>
  3d1d06:	48 83 3d 22 7e 52 00 	cmpq   $0x0,0x527e22(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d1d0d:	00 
  3d1d0e:	74 15                	je     3d1d25 <_ZN5MCLoc11RelocWithPFEv+0x2ff5>
  3d1d10:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d1d15:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d1d1b:	83 f8 01             	cmp    $0x1,%eax
  3d1d1e:	74 19                	je     3d1d39 <_ZN5MCLoc11RelocWithPFEv+0x3009>
  3d1d20:	e9 b0 01 00 00       	jmp    3d1ed5 <_ZN5MCLoc11RelocWithPFEv+0x31a5>
  3d1d25:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d1d29:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d1d2c:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d1d30:	83 f8 01             	cmp    $0x1,%eax
  3d1d33:	0f 85 9c 01 00 00    	jne    3d1ed5 <_ZN5MCLoc11RelocWithPFEv+0x31a5>
  3d1d39:	49 8b 07             	mov    (%r15),%rax
  3d1d3c:	4c 89 ff             	mov    %r15,%rdi
  3d1d3f:	ff 50 10             	call   *0x10(%rax)
  3d1d42:	48 83 3d e6 7d 52 00 	cmpq   $0x0,0x527de6(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d1d49:	00 
  3d1d4a:	74 15                	je     3d1d61 <_ZN5MCLoc11RelocWithPFEv+0x3031>
  3d1d4c:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d1d51:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d1d57:	83 f8 01             	cmp    $0x1,%eax
  3d1d5a:	74 19                	je     3d1d75 <_ZN5MCLoc11RelocWithPFEv+0x3045>
  3d1d5c:	e9 74 01 00 00       	jmp    3d1ed5 <_ZN5MCLoc11RelocWithPFEv+0x31a5>
  3d1d61:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d1d65:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d1d68:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d1d6c:	83 f8 01             	cmp    $0x1,%eax
  3d1d6f:	0f 85 60 01 00 00    	jne    3d1ed5 <_ZN5MCLoc11RelocWithPFEv+0x31a5>
  3d1d75:	49 8b 07             	mov    (%r15),%rax
  3d1d78:	4c 89 ff             	mov    %r15,%rdi
  3d1d7b:	ff 50 18             	call   *0x18(%rax)
  3d1d7e:	e9 52 01 00 00       	jmp    3d1ed5 <_ZN5MCLoc11RelocWithPFEv+0x31a5>
  3d1d83:	49 89 c6             	mov    %rax,%r14
  3d1d86:	e9 ac 01 00 00       	jmp    3d1f37 <_ZN5MCLoc11RelocWithPFEv+0x3207>
  3d1d8b:	49 89 c6             	mov    %rax,%r14
  3d1d8e:	4d 39 ef             	cmp    %r13,%r15
  3d1d91:	0f 84 b9 01 00 00    	je     3d1f50 <_ZN5MCLoc11RelocWithPFEv+0x3220>
  3d1d97:	4c 89 ff             	mov    %r15,%rdi
  3d1d9a:	e8 51 db dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d1d9f:	e9 ac 01 00 00       	jmp    3d1f50 <_ZN5MCLoc11RelocWithPFEv+0x3220>
  3d1da4:	49 89 c6             	mov    %rax,%r14
  3d1da7:	e9 b8 01 00 00       	jmp    3d1f64 <_ZN5MCLoc11RelocWithPFEv+0x3234>
  3d1dac:	e9 f1 01 00 00       	jmp    3d1fa2 <_ZN5MCLoc11RelocWithPFEv+0x3272>
  3d1db1:	e9 5c 14 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d1db6:	49 89 c6             	mov    %rax,%r14
  3d1db9:	4d 85 e4             	test   %r12,%r12
  3d1dbc:	0f 84 c2 02 00 00    	je     3d2084 <_ZN5MCLoc11RelocWithPFEv+0x3354>
  3d1dc2:	48 83 3d 66 7d 52 00 	cmpq   $0x0,0x527d66(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d1dc9:	00 
  3d1dca:	74 16                	je     3d1de2 <_ZN5MCLoc11RelocWithPFEv+0x30b2>
  3d1dcc:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d1dd1:	f0 41 0f c1 44 24 08 	lock xadd %eax,0x8(%r12)
  3d1dd8:	83 f8 01             	cmp    $0x1,%eax
  3d1ddb:	74 1b                	je     3d1df8 <_ZN5MCLoc11RelocWithPFEv+0x30c8>
  3d1ddd:	e9 a2 02 00 00       	jmp    3d2084 <_ZN5MCLoc11RelocWithPFEv+0x3354>
  3d1de2:	41 8b 44 24 08       	mov    0x8(%r12),%eax
  3d1de7:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d1dea:	41 89 4c 24 08       	mov    %ecx,0x8(%r12)
  3d1def:	83 f8 01             	cmp    $0x1,%eax
  3d1df2:	0f 85 8c 02 00 00    	jne    3d2084 <_ZN5MCLoc11RelocWithPFEv+0x3354>
  3d1df8:	49 8b 04 24          	mov    (%r12),%rax
  3d1dfc:	4c 89 e7             	mov    %r12,%rdi
  3d1dff:	ff 50 10             	call   *0x10(%rax)
  3d1e02:	48 83 3d 26 7d 52 00 	cmpq   $0x0,0x527d26(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d1e09:	00 
  3d1e0a:	74 16                	je     3d1e22 <_ZN5MCLoc11RelocWithPFEv+0x30f2>
  3d1e0c:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d1e11:	f0 41 0f c1 44 24 0c 	lock xadd %eax,0xc(%r12)
  3d1e18:	83 f8 01             	cmp    $0x1,%eax
  3d1e1b:	74 1b                	je     3d1e38 <_ZN5MCLoc11RelocWithPFEv+0x3108>
  3d1e1d:	e9 62 02 00 00       	jmp    3d2084 <_ZN5MCLoc11RelocWithPFEv+0x3354>
  3d1e22:	41 8b 44 24 0c       	mov    0xc(%r12),%eax
  3d1e27:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d1e2a:	41 89 4c 24 0c       	mov    %ecx,0xc(%r12)
  3d1e2f:	83 f8 01             	cmp    $0x1,%eax
  3d1e32:	0f 85 4c 02 00 00    	jne    3d2084 <_ZN5MCLoc11RelocWithPFEv+0x3354>
  3d1e38:	49 8b 04 24          	mov    (%r12),%rax
  3d1e3c:	4c 89 e7             	mov    %r12,%rdi
  3d1e3f:	ff 50 18             	call   *0x18(%rax)
  3d1e42:	e9 3d 02 00 00       	jmp    3d2084 <_ZN5MCLoc11RelocWithPFEv+0x3354>
  3d1e47:	49 89 c6             	mov    %rax,%r14
  3d1e4a:	e9 9e 02 00 00       	jmp    3d20ed <_ZN5MCLoc11RelocWithPFEv+0x33bd>
  3d1e4f:	49 89 c6             	mov    %rax,%r14
  3d1e52:	4d 39 ec             	cmp    %r13,%r12
  3d1e55:	0f 84 ab 02 00 00    	je     3d2106 <_ZN5MCLoc11RelocWithPFEv+0x33d6>
  3d1e5b:	4c 89 e7             	mov    %r12,%rdi
  3d1e5e:	e8 8d da dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d1e63:	e9 9e 02 00 00       	jmp    3d2106 <_ZN5MCLoc11RelocWithPFEv+0x33d6>
  3d1e68:	49 89 c6             	mov    %rax,%r14
  3d1e6b:	e9 aa 02 00 00       	jmp    3d211a <_ZN5MCLoc11RelocWithPFEv+0x33ea>
  3d1e70:	49 89 c6             	mov    %rax,%r14
  3d1e73:	e9 b6 02 00 00       	jmp    3d212e <_ZN5MCLoc11RelocWithPFEv+0x33fe>
  3d1e78:	49 89 c6             	mov    %rax,%r14
  3d1e7b:	e9 ae 02 00 00       	jmp    3d212e <_ZN5MCLoc11RelocWithPFEv+0x33fe>
  3d1e80:	e9 8d 13 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d1e85:	e9 88 13 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d1e8a:	e9 e9 04 00 00       	jmp    3d2378 <_ZN5MCLoc11RelocWithPFEv+0x3648>
  3d1e8f:	e9 ec 04 00 00       	jmp    3d2380 <_ZN5MCLoc11RelocWithPFEv+0x3650>
  3d1e94:	48 89 c7             	mov    %rax,%rdi
  3d1e97:	e8 64 12 df ff       	call   1c3100 <__clang_call_terminate>
  3d1e9c:	48 89 c7             	mov    %rax,%rdi
  3d1e9f:	e8 5c 12 df ff       	call   1c3100 <__clang_call_terminate>
  3d1ea4:	48 89 c7             	mov    %rax,%rdi
  3d1ea7:	e8 54 12 df ff       	call   1c3100 <__clang_call_terminate>
  3d1eac:	48 89 c7             	mov    %rax,%rdi
  3d1eaf:	e8 4c 12 df ff       	call   1c3100 <__clang_call_terminate>
  3d1eb4:	e9 59 13 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d1eb9:	49 89 c6             	mov    %rax,%r14
  3d1ebc:	48 8b 4c 24 38       	mov    0x38(%rsp),%rcx
  3d1ec1:	48 85 c9             	test   %rcx,%rcx
  3d1ec4:	74 0f                	je     3d1ed5 <_ZN5MCLoc11RelocWithPFEv+0x31a5>
  3d1ec6:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3d1ecb:	ba 03 00 00 00       	mov    $0x3,%edx
  3d1ed0:	48 89 fe             	mov    %rdi,%rsi
  3d1ed3:	ff d1                	call   *%rcx
  3d1ed5:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3d1eda:	4d 85 ff             	test   %r15,%r15
  3d1edd:	74 58                	je     3d1f37 <_ZN5MCLoc11RelocWithPFEv+0x3207>
  3d1edf:	48 83 3d 49 7c 52 00 	cmpq   $0x0,0x527c49(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d1ee6:	00 
  3d1ee7:	74 12                	je     3d1efb <_ZN5MCLoc11RelocWithPFEv+0x31cb>
  3d1ee9:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d1eee:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d1ef4:	83 f8 01             	cmp    $0x1,%eax
  3d1ef7:	74 12                	je     3d1f0b <_ZN5MCLoc11RelocWithPFEv+0x31db>
  3d1ef9:	eb 3c                	jmp    3d1f37 <_ZN5MCLoc11RelocWithPFEv+0x3207>
  3d1efb:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d1eff:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d1f02:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d1f06:	83 f8 01             	cmp    $0x1,%eax
  3d1f09:	75 2c                	jne    3d1f37 <_ZN5MCLoc11RelocWithPFEv+0x3207>
  3d1f0b:	49 8b 07             	mov    (%r15),%rax
  3d1f0e:	4c 89 ff             	mov    %r15,%rdi
  3d1f11:	ff 50 10             	call   *0x10(%rax)
  3d1f14:	48 83 3d 14 7c 52 00 	cmpq   $0x0,0x527c14(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d1f1b:	00 
  3d1f1c:	74 62                	je     3d1f80 <_ZN5MCLoc11RelocWithPFEv+0x3250>
  3d1f1e:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d1f23:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d1f29:	83 f8 01             	cmp    $0x1,%eax
  3d1f2c:	75 09                	jne    3d1f37 <_ZN5MCLoc11RelocWithPFEv+0x3207>
  3d1f2e:	49 8b 07             	mov    (%r15),%rax
  3d1f31:	4c 89 ff             	mov    %r15,%rdi
  3d1f34:	ff 50 18             	call   *0x18(%rax)
  3d1f37:	48 8b 4c 24 78       	mov    0x78(%rsp),%rcx
  3d1f3c:	48 85 c9             	test   %rcx,%rcx
  3d1f3f:	74 0f                	je     3d1f50 <_ZN5MCLoc11RelocWithPFEv+0x3220>
  3d1f41:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3d1f46:	ba 03 00 00 00       	mov    $0x3,%edx
  3d1f4b:	48 89 fe             	mov    %rdi,%rsi
  3d1f4e:	ff d1                	call   *%rcx
  3d1f50:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d1f55:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d1f5a:	48 39 c7             	cmp    %rax,%rdi
  3d1f5d:	74 05                	je     3d1f64 <_ZN5MCLoc11RelocWithPFEv+0x3234>
  3d1f5f:	e8 8c d9 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d1f64:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3d1f6b:	00 
  3d1f6c:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3d1f73:	00 
  3d1f74:	48 39 c7             	cmp    %rax,%rdi
  3d1f77:	74 2c                	je     3d1fa5 <_ZN5MCLoc11RelocWithPFEv+0x3275>
  3d1f79:	e8 72 d9 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d1f7e:	eb 25                	jmp    3d1fa5 <_ZN5MCLoc11RelocWithPFEv+0x3275>
  3d1f80:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d1f84:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d1f87:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d1f8b:	83 f8 01             	cmp    $0x1,%eax
  3d1f8e:	75 a7                	jne    3d1f37 <_ZN5MCLoc11RelocWithPFEv+0x3207>
  3d1f90:	eb 9c                	jmp    3d1f2e <_ZN5MCLoc11RelocWithPFEv+0x31fe>
  3d1f92:	48 89 c7             	mov    %rax,%rdi
  3d1f95:	e8 66 11 df ff       	call   1c3100 <__clang_call_terminate>
  3d1f9a:	48 89 c7             	mov    %rax,%rdi
  3d1f9d:	e8 5e 11 df ff       	call   1c3100 <__clang_call_terminate>
  3d1fa2:	49 89 c6             	mov    %rax,%r14
  3d1fa5:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3d1fac:	00 
  3d1fad:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d1fb4:	00 
  3d1fb5:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d1fb9:	48 8b 8c 24 b8 00 00 	mov    0xb8(%rsp),%rcx
  3d1fc0:	00 
  3d1fc1:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d1fc8:	00 
  3d1fc9:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  3d1fd0:	00 
  3d1fd1:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d1fd8:	00 
  3d1fd9:	48 8b 84 24 c8 00 00 	mov    0xc8(%rsp),%rax
  3d1fe0:	00 
  3d1fe1:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d1fe8:	00 
  3d1fe9:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d1ff0:	00 
  3d1ff1:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d1ff8:	00 
  3d1ff9:	48 39 c7             	cmp    %rax,%rdi
  3d1ffc:	74 05                	je     3d2003 <_ZN5MCLoc11RelocWithPFEv+0x32d3>
  3d1ffe:	e8 ed d8 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2003:	48 8b 84 24 d0 00 00 	mov    0xd0(%rsp),%rax
  3d200a:	00 
  3d200b:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d2012:	00 
  3d2013:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d201a:	00 
  3d201b:	e8 e0 1a de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d2020:	48 8b 84 24 d8 00 00 	mov    0xd8(%rsp),%rax
  3d2027:	00 
  3d2028:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d202f:	00 
  3d2030:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d2034:	48 8b 8c 24 e0 00 00 	mov    0xe0(%rsp),%rcx
  3d203b:	00 
  3d203c:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d2043:	00 
  3d2044:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d204b:	00 00 00 00 00 
  3d2050:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d2057:	00 
  3d2058:	e8 63 66 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3d205d:	e9 be 11 00 00       	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d2062:	49 89 c6             	mov    %rax,%r14
  3d2065:	48 8b 8c 24 a0 00 00 	mov    0xa0(%rsp),%rcx
  3d206c:	00 
  3d206d:	48 85 c9             	test   %rcx,%rcx
  3d2070:	74 12                	je     3d2084 <_ZN5MCLoc11RelocWithPFEv+0x3354>
  3d2072:	48 8d bc 24 90 00 00 	lea    0x90(%rsp),%rdi
  3d2079:	00 
  3d207a:	ba 03 00 00 00       	mov    $0x3,%edx
  3d207f:	48 89 fe             	mov    %rdi,%rsi
  3d2082:	ff d1                	call   *%rcx
  3d2084:	4c 8b bc 24 d8 02 00 	mov    0x2d8(%rsp),%r15
  3d208b:	00 
  3d208c:	4d 85 ff             	test   %r15,%r15
  3d208f:	74 5c                	je     3d20ed <_ZN5MCLoc11RelocWithPFEv+0x33bd>
  3d2091:	48 83 3d 97 7a 52 00 	cmpq   $0x0,0x527a97(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2098:	00 
  3d2099:	74 12                	je     3d20ad <_ZN5MCLoc11RelocWithPFEv+0x337d>
  3d209b:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d20a0:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d20a6:	83 f8 01             	cmp    $0x1,%eax
  3d20a9:	74 12                	je     3d20bd <_ZN5MCLoc11RelocWithPFEv+0x338d>
  3d20ab:	eb 40                	jmp    3d20ed <_ZN5MCLoc11RelocWithPFEv+0x33bd>
  3d20ad:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d20b1:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d20b4:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d20b8:	83 f8 01             	cmp    $0x1,%eax
  3d20bb:	75 30                	jne    3d20ed <_ZN5MCLoc11RelocWithPFEv+0x33bd>
  3d20bd:	49 8b 07             	mov    (%r15),%rax
  3d20c0:	4c 89 ff             	mov    %r15,%rdi
  3d20c3:	ff 50 10             	call   *0x10(%rax)
  3d20c6:	48 83 3d 62 7a 52 00 	cmpq   $0x0,0x527a62(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d20cd:	00 
  3d20ce:	0f 84 17 01 00 00    	je     3d21eb <_ZN5MCLoc11RelocWithPFEv+0x34bb>
  3d20d4:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d20d9:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d20df:	83 f8 01             	cmp    $0x1,%eax
  3d20e2:	75 09                	jne    3d20ed <_ZN5MCLoc11RelocWithPFEv+0x33bd>
  3d20e4:	49 8b 07             	mov    (%r15),%rax
  3d20e7:	4c 89 ff             	mov    %r15,%rdi
  3d20ea:	ff 50 18             	call   *0x18(%rax)
  3d20ed:	48 8b 4c 24 38       	mov    0x38(%rsp),%rcx
  3d20f2:	48 85 c9             	test   %rcx,%rcx
  3d20f5:	74 0f                	je     3d2106 <_ZN5MCLoc11RelocWithPFEv+0x33d6>
  3d20f7:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3d20fc:	ba 03 00 00 00       	mov    $0x3,%edx
  3d2101:	48 89 fe             	mov    %rdi,%rsi
  3d2104:	ff d1                	call   *%rcx
  3d2106:	48 8b 7c 24 48       	mov    0x48(%rsp),%rdi
  3d210b:	48 8d 44 24 58       	lea    0x58(%rsp),%rax
  3d2110:	48 39 c7             	cmp    %rax,%rdi
  3d2113:	74 05                	je     3d211a <_ZN5MCLoc11RelocWithPFEv+0x33ea>
  3d2115:	e8 d6 d7 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d211a:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d211f:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d2124:	48 39 c7             	cmp    %rax,%rdi
  3d2127:	74 05                	je     3d212e <_ZN5MCLoc11RelocWithPFEv+0x33fe>
  3d2129:	e8 c2 d7 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d212e:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3d2135:	00 
  3d2136:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d213d:	00 
  3d213e:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d2142:	48 8b 8c 24 b8 00 00 	mov    0xb8(%rsp),%rcx
  3d2149:	00 
  3d214a:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d2151:	00 
  3d2152:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  3d2159:	00 
  3d215a:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d2161:	00 
  3d2162:	48 8b 84 24 c8 00 00 	mov    0xc8(%rsp),%rax
  3d2169:	00 
  3d216a:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d2171:	00 
  3d2172:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d2179:	00 
  3d217a:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d2181:	00 
  3d2182:	48 39 c7             	cmp    %rax,%rdi
  3d2185:	74 05                	je     3d218c <_ZN5MCLoc11RelocWithPFEv+0x345c>
  3d2187:	e8 64 d7 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d218c:	48 8b 84 24 d0 00 00 	mov    0xd0(%rsp),%rax
  3d2193:	00 
  3d2194:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d219b:	00 
  3d219c:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d21a3:	00 
  3d21a4:	e8 57 19 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d21a9:	48 8b 84 24 d8 00 00 	mov    0xd8(%rsp),%rax
  3d21b0:	00 
  3d21b1:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d21b8:	00 
  3d21b9:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d21bd:	48 8b 8c 24 e0 00 00 	mov    0xe0(%rsp),%rcx
  3d21c4:	00 
  3d21c5:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d21cc:	00 
  3d21cd:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d21d4:	00 00 00 00 00 
  3d21d9:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d21e0:	00 
  3d21e1:	e8 da 64 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3d21e6:	e9 35 10 00 00       	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d21eb:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d21ef:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d21f2:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d21f6:	83 f8 01             	cmp    $0x1,%eax
  3d21f9:	0f 85 ee fe ff ff    	jne    3d20ed <_ZN5MCLoc11RelocWithPFEv+0x33bd>
  3d21ff:	e9 e0 fe ff ff       	jmp    3d20e4 <_ZN5MCLoc11RelocWithPFEv+0x33b4>
  3d2204:	48 89 c7             	mov    %rax,%rdi
  3d2207:	e8 f4 0e df ff       	call   1c3100 <__clang_call_terminate>
  3d220c:	48 89 c7             	mov    %rax,%rdi
  3d220f:	e8 ec 0e df ff       	call   1c3100 <__clang_call_terminate>
  3d2214:	49 89 c6             	mov    %rax,%r14
  3d2217:	4d 85 e4             	test   %r12,%r12
  3d221a:	0f 84 48 02 00 00    	je     3d2468 <_ZN5MCLoc11RelocWithPFEv+0x3738>
  3d2220:	48 83 3d 08 79 52 00 	cmpq   $0x0,0x527908(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2227:	00 
  3d2228:	74 16                	je     3d2240 <_ZN5MCLoc11RelocWithPFEv+0x3510>
  3d222a:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d222f:	f0 41 0f c1 44 24 08 	lock xadd %eax,0x8(%r12)
  3d2236:	83 f8 01             	cmp    $0x1,%eax
  3d2239:	74 1b                	je     3d2256 <_ZN5MCLoc11RelocWithPFEv+0x3526>
  3d223b:	e9 28 02 00 00       	jmp    3d2468 <_ZN5MCLoc11RelocWithPFEv+0x3738>
  3d2240:	41 8b 44 24 08       	mov    0x8(%r12),%eax
  3d2245:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2248:	41 89 4c 24 08       	mov    %ecx,0x8(%r12)
  3d224d:	83 f8 01             	cmp    $0x1,%eax
  3d2250:	0f 85 12 02 00 00    	jne    3d2468 <_ZN5MCLoc11RelocWithPFEv+0x3738>
  3d2256:	49 8b 04 24          	mov    (%r12),%rax
  3d225a:	4c 89 e7             	mov    %r12,%rdi
  3d225d:	ff 50 10             	call   *0x10(%rax)
  3d2260:	48 83 3d c8 78 52 00 	cmpq   $0x0,0x5278c8(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2267:	00 
  3d2268:	74 16                	je     3d2280 <_ZN5MCLoc11RelocWithPFEv+0x3550>
  3d226a:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d226f:	f0 41 0f c1 44 24 0c 	lock xadd %eax,0xc(%r12)
  3d2276:	83 f8 01             	cmp    $0x1,%eax
  3d2279:	74 1b                	je     3d2296 <_ZN5MCLoc11RelocWithPFEv+0x3566>
  3d227b:	e9 e8 01 00 00       	jmp    3d2468 <_ZN5MCLoc11RelocWithPFEv+0x3738>
  3d2280:	41 8b 44 24 0c       	mov    0xc(%r12),%eax
  3d2285:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2288:	41 89 4c 24 0c       	mov    %ecx,0xc(%r12)
  3d228d:	83 f8 01             	cmp    $0x1,%eax
  3d2290:	0f 85 d2 01 00 00    	jne    3d2468 <_ZN5MCLoc11RelocWithPFEv+0x3738>
  3d2296:	49 8b 04 24          	mov    (%r12),%rax
  3d229a:	4c 89 e7             	mov    %r12,%rdi
  3d229d:	ff 50 18             	call   *0x18(%rax)
  3d22a0:	e9 c3 01 00 00       	jmp    3d2468 <_ZN5MCLoc11RelocWithPFEv+0x3738>
  3d22a5:	49 89 c6             	mov    %rax,%r14
  3d22a8:	4d 85 e4             	test   %r12,%r12
  3d22ab:	0f 84 66 03 00 00    	je     3d2617 <_ZN5MCLoc11RelocWithPFEv+0x38e7>
  3d22b1:	48 83 3d 77 78 52 00 	cmpq   $0x0,0x527877(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d22b8:	00 
  3d22b9:	74 16                	je     3d22d1 <_ZN5MCLoc11RelocWithPFEv+0x35a1>
  3d22bb:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d22c0:	f0 41 0f c1 44 24 08 	lock xadd %eax,0x8(%r12)
  3d22c7:	83 f8 01             	cmp    $0x1,%eax
  3d22ca:	74 1b                	je     3d22e7 <_ZN5MCLoc11RelocWithPFEv+0x35b7>
  3d22cc:	e9 46 03 00 00       	jmp    3d2617 <_ZN5MCLoc11RelocWithPFEv+0x38e7>
  3d22d1:	41 8b 44 24 08       	mov    0x8(%r12),%eax
  3d22d6:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d22d9:	41 89 4c 24 08       	mov    %ecx,0x8(%r12)
  3d22de:	83 f8 01             	cmp    $0x1,%eax
  3d22e1:	0f 85 30 03 00 00    	jne    3d2617 <_ZN5MCLoc11RelocWithPFEv+0x38e7>
  3d22e7:	49 8b 04 24          	mov    (%r12),%rax
  3d22eb:	4c 89 e7             	mov    %r12,%rdi
  3d22ee:	ff 50 10             	call   *0x10(%rax)
  3d22f1:	48 83 3d 37 78 52 00 	cmpq   $0x0,0x527837(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d22f8:	00 
  3d22f9:	74 16                	je     3d2311 <_ZN5MCLoc11RelocWithPFEv+0x35e1>
  3d22fb:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d2300:	f0 41 0f c1 44 24 0c 	lock xadd %eax,0xc(%r12)
  3d2307:	83 f8 01             	cmp    $0x1,%eax
  3d230a:	74 1b                	je     3d2327 <_ZN5MCLoc11RelocWithPFEv+0x35f7>
  3d230c:	e9 06 03 00 00       	jmp    3d2617 <_ZN5MCLoc11RelocWithPFEv+0x38e7>
  3d2311:	41 8b 44 24 0c       	mov    0xc(%r12),%eax
  3d2316:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2319:	41 89 4c 24 0c       	mov    %ecx,0xc(%r12)
  3d231e:	83 f8 01             	cmp    $0x1,%eax
  3d2321:	0f 85 f0 02 00 00    	jne    3d2617 <_ZN5MCLoc11RelocWithPFEv+0x38e7>
  3d2327:	49 8b 04 24          	mov    (%r12),%rax
  3d232b:	4c 89 e7             	mov    %r12,%rdi
  3d232e:	ff 50 18             	call   *0x18(%rax)
  3d2331:	e9 e1 02 00 00       	jmp    3d2617 <_ZN5MCLoc11RelocWithPFEv+0x38e7>
  3d2336:	49 89 c6             	mov    %rax,%r14
  3d2339:	e9 90 01 00 00       	jmp    3d24ce <_ZN5MCLoc11RelocWithPFEv+0x379e>
  3d233e:	49 89 c6             	mov    %rax,%r14
  3d2341:	e9 37 03 00 00       	jmp    3d267d <_ZN5MCLoc11RelocWithPFEv+0x394d>
  3d2346:	49 89 c6             	mov    %rax,%r14
  3d2349:	4d 39 ec             	cmp    %r13,%r12
  3d234c:	0f 84 95 01 00 00    	je     3d24e7 <_ZN5MCLoc11RelocWithPFEv+0x37b7>
  3d2352:	4c 89 e7             	mov    %r12,%rdi
  3d2355:	e8 96 d5 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d235a:	e9 88 01 00 00       	jmp    3d24e7 <_ZN5MCLoc11RelocWithPFEv+0x37b7>
  3d235f:	49 89 c6             	mov    %rax,%r14
  3d2362:	4d 39 ec             	cmp    %r13,%r12
  3d2365:	0f 84 2b 03 00 00    	je     3d2696 <_ZN5MCLoc11RelocWithPFEv+0x3966>
  3d236b:	4c 89 e7             	mov    %r12,%rdi
  3d236e:	e8 7d d5 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2373:	e9 1e 03 00 00       	jmp    3d2696 <_ZN5MCLoc11RelocWithPFEv+0x3966>
  3d2378:	49 89 c6             	mov    %rax,%r14
  3d237b:	e9 7b 01 00 00       	jmp    3d24fb <_ZN5MCLoc11RelocWithPFEv+0x37cb>
  3d2380:	49 89 c6             	mov    %rax,%r14
  3d2383:	e9 22 03 00 00       	jmp    3d26aa <_ZN5MCLoc11RelocWithPFEv+0x397a>
  3d2388:	49 89 c6             	mov    %rax,%r14
  3d238b:	e9 85 01 00 00       	jmp    3d2515 <_ZN5MCLoc11RelocWithPFEv+0x37e5>
  3d2390:	49 89 c6             	mov    %rax,%r14
  3d2393:	e9 2c 03 00 00       	jmp    3d26c4 <_ZN5MCLoc11RelocWithPFEv+0x3994>
  3d2398:	49 89 c6             	mov    %rax,%r14
  3d239b:	e9 75 01 00 00       	jmp    3d2515 <_ZN5MCLoc11RelocWithPFEv+0x37e5>
  3d23a0:	49 89 c6             	mov    %rax,%r14
  3d23a3:	e9 1c 03 00 00       	jmp    3d26c4 <_ZN5MCLoc11RelocWithPFEv+0x3994>
  3d23a8:	e9 65 0e 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d23ad:	e9 60 0e 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d23b2:	49 89 c6             	mov    %rax,%r14
  3d23b5:	48 8b bc 24 40 01 00 	mov    0x140(%rsp),%rdi
  3d23bc:	00 
  3d23bd:	4c 39 ff             	cmp    %r15,%rdi
  3d23c0:	0f 84 5a 0e 00 00    	je     3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d23c6:	e8 25 d5 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d23cb:	e9 50 0e 00 00       	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d23d0:	49 89 c6             	mov    %rax,%r14
  3d23d3:	48 8b bc 24 40 01 00 	mov    0x140(%rsp),%rdi
  3d23da:	00 
  3d23db:	4c 39 ff             	cmp    %r15,%rdi
  3d23de:	0f 84 3c 0e 00 00    	je     3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d23e4:	e8 07 d5 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d23e9:	e9 32 0e 00 00       	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d23ee:	e9 63 04 00 00       	jmp    3d2856 <_ZN5MCLoc11RelocWithPFEv+0x3b26>
  3d23f3:	e9 1a 0e 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d23f8:	e9 4e 05 00 00       	jmp    3d294b <_ZN5MCLoc11RelocWithPFEv+0x3c1b>
  3d23fd:	e9 e2 06 00 00       	jmp    3d2ae4 <_ZN5MCLoc11RelocWithPFEv+0x3db4>
  3d2402:	e9 e5 06 00 00       	jmp    3d2aec <_ZN5MCLoc11RelocWithPFEv+0x3dbc>
  3d2407:	48 89 c7             	mov    %rax,%rdi
  3d240a:	e8 f1 0c df ff       	call   1c3100 <__clang_call_terminate>
  3d240f:	48 89 c7             	mov    %rax,%rdi
  3d2412:	e8 e9 0c df ff       	call   1c3100 <__clang_call_terminate>
  3d2417:	48 89 c7             	mov    %rax,%rdi
  3d241a:	e8 e1 0c df ff       	call   1c3100 <__clang_call_terminate>
  3d241f:	48 89 c7             	mov    %rax,%rdi
  3d2422:	e8 d9 0c df ff       	call   1c3100 <__clang_call_terminate>
  3d2427:	48 89 c7             	mov    %rax,%rdi
  3d242a:	e8 d1 0c df ff       	call   1c3100 <__clang_call_terminate>
  3d242f:	48 89 c7             	mov    %rax,%rdi
  3d2432:	e8 c9 0c df ff       	call   1c3100 <__clang_call_terminate>
  3d2437:	48 89 c7             	mov    %rax,%rdi
  3d243a:	e8 c1 0c df ff       	call   1c3100 <__clang_call_terminate>
  3d243f:	48 89 c7             	mov    %rax,%rdi
  3d2442:	e8 b9 0c df ff       	call   1c3100 <__clang_call_terminate>
  3d2447:	e9 c6 0d 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d244c:	49 89 c6             	mov    %rax,%r14
  3d244f:	48 8b 4c 24 38       	mov    0x38(%rsp),%rcx
  3d2454:	48 85 c9             	test   %rcx,%rcx
  3d2457:	74 0f                	je     3d2468 <_ZN5MCLoc11RelocWithPFEv+0x3738>
  3d2459:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3d245e:	ba 03 00 00 00       	mov    $0x3,%edx
  3d2463:	48 89 fe             	mov    %rdi,%rsi
  3d2466:	ff d1                	call   *%rcx
  3d2468:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3d246d:	4d 85 ff             	test   %r15,%r15
  3d2470:	74 5c                	je     3d24ce <_ZN5MCLoc11RelocWithPFEv+0x379e>
  3d2472:	48 83 3d b6 76 52 00 	cmpq   $0x0,0x5276b6(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2479:	00 
  3d247a:	74 12                	je     3d248e <_ZN5MCLoc11RelocWithPFEv+0x375e>
  3d247c:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d2481:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d2487:	83 f8 01             	cmp    $0x1,%eax
  3d248a:	74 12                	je     3d249e <_ZN5MCLoc11RelocWithPFEv+0x376e>
  3d248c:	eb 40                	jmp    3d24ce <_ZN5MCLoc11RelocWithPFEv+0x379e>
  3d248e:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d2492:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2495:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d2499:	83 f8 01             	cmp    $0x1,%eax
  3d249c:	75 30                	jne    3d24ce <_ZN5MCLoc11RelocWithPFEv+0x379e>
  3d249e:	49 8b 07             	mov    (%r15),%rax
  3d24a1:	4c 89 ff             	mov    %r15,%rdi
  3d24a4:	ff 50 10             	call   *0x10(%rax)
  3d24a7:	48 83 3d 81 76 52 00 	cmpq   $0x0,0x527681(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d24ae:	00 
  3d24af:	0f 84 1d 01 00 00    	je     3d25d2 <_ZN5MCLoc11RelocWithPFEv+0x38a2>
  3d24b5:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d24ba:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d24c0:	83 f8 01             	cmp    $0x1,%eax
  3d24c3:	75 09                	jne    3d24ce <_ZN5MCLoc11RelocWithPFEv+0x379e>
  3d24c5:	49 8b 07             	mov    (%r15),%rax
  3d24c8:	4c 89 ff             	mov    %r15,%rdi
  3d24cb:	ff 50 18             	call   *0x18(%rax)
  3d24ce:	48 8b 4c 24 78       	mov    0x78(%rsp),%rcx
  3d24d3:	48 85 c9             	test   %rcx,%rcx
  3d24d6:	74 0f                	je     3d24e7 <_ZN5MCLoc11RelocWithPFEv+0x37b7>
  3d24d8:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3d24dd:	ba 03 00 00 00       	mov    $0x3,%edx
  3d24e2:	48 89 fe             	mov    %rdi,%rsi
  3d24e5:	ff d1                	call   *%rcx
  3d24e7:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d24ec:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d24f1:	48 39 c7             	cmp    %rax,%rdi
  3d24f4:	74 05                	je     3d24fb <_ZN5MCLoc11RelocWithPFEv+0x37cb>
  3d24f6:	e8 f5 d3 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d24fb:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3d2502:	00 
  3d2503:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3d250a:	00 
  3d250b:	48 39 c7             	cmp    %rax,%rdi
  3d250e:	74 05                	je     3d2515 <_ZN5MCLoc11RelocWithPFEv+0x37e5>
  3d2510:	e8 db d3 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2515:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3d251c:	00 
  3d251d:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d2524:	00 
  3d2525:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d2529:	48 8b 8c 24 b8 00 00 	mov    0xb8(%rsp),%rcx
  3d2530:	00 
  3d2531:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d2538:	00 
  3d2539:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  3d2540:	00 
  3d2541:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d2548:	00 
  3d2549:	48 8b 84 24 c8 00 00 	mov    0xc8(%rsp),%rax
  3d2550:	00 
  3d2551:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d2558:	00 
  3d2559:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d2560:	00 
  3d2561:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d2568:	00 
  3d2569:	48 39 c7             	cmp    %rax,%rdi
  3d256c:	74 05                	je     3d2573 <_ZN5MCLoc11RelocWithPFEv+0x3843>
  3d256e:	e8 7d d3 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2573:	48 8b 84 24 d0 00 00 	mov    0xd0(%rsp),%rax
  3d257a:	00 
  3d257b:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d2582:	00 
  3d2583:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d258a:	00 
  3d258b:	e8 70 15 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d2590:	48 8b 84 24 d8 00 00 	mov    0xd8(%rsp),%rax
  3d2597:	00 
  3d2598:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d259f:	00 
  3d25a0:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d25a4:	48 8b 8c 24 e0 00 00 	mov    0xe0(%rsp),%rcx
  3d25ab:	00 
  3d25ac:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d25b3:	00 
  3d25b4:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d25bb:	00 00 00 00 00 
  3d25c0:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d25c7:	00 
  3d25c8:	e8 f3 60 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3d25cd:	e9 4e 0c 00 00       	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d25d2:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d25d6:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d25d9:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d25dd:	83 f8 01             	cmp    $0x1,%eax
  3d25e0:	0f 85 e8 fe ff ff    	jne    3d24ce <_ZN5MCLoc11RelocWithPFEv+0x379e>
  3d25e6:	e9 da fe ff ff       	jmp    3d24c5 <_ZN5MCLoc11RelocWithPFEv+0x3795>
  3d25eb:	48 89 c7             	mov    %rax,%rdi
  3d25ee:	e8 0d 0b df ff       	call   1c3100 <__clang_call_terminate>
  3d25f3:	48 89 c7             	mov    %rax,%rdi
  3d25f6:	e8 05 0b df ff       	call   1c3100 <__clang_call_terminate>
  3d25fb:	49 89 c6             	mov    %rax,%r14
  3d25fe:	48 8b 4c 24 38       	mov    0x38(%rsp),%rcx
  3d2603:	48 85 c9             	test   %rcx,%rcx
  3d2606:	74 0f                	je     3d2617 <_ZN5MCLoc11RelocWithPFEv+0x38e7>
  3d2608:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3d260d:	ba 03 00 00 00       	mov    $0x3,%edx
  3d2612:	48 89 fe             	mov    %rdi,%rsi
  3d2615:	ff d1                	call   *%rcx
  3d2617:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3d261c:	4d 85 ff             	test   %r15,%r15
  3d261f:	74 5c                	je     3d267d <_ZN5MCLoc11RelocWithPFEv+0x394d>
  3d2621:	48 83 3d 07 75 52 00 	cmpq   $0x0,0x527507(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2628:	00 
  3d2629:	74 12                	je     3d263d <_ZN5MCLoc11RelocWithPFEv+0x390d>
  3d262b:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d2630:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d2636:	83 f8 01             	cmp    $0x1,%eax
  3d2639:	74 12                	je     3d264d <_ZN5MCLoc11RelocWithPFEv+0x391d>
  3d263b:	eb 40                	jmp    3d267d <_ZN5MCLoc11RelocWithPFEv+0x394d>
  3d263d:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d2641:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2644:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d2648:	83 f8 01             	cmp    $0x1,%eax
  3d264b:	75 30                	jne    3d267d <_ZN5MCLoc11RelocWithPFEv+0x394d>
  3d264d:	49 8b 07             	mov    (%r15),%rax
  3d2650:	4c 89 ff             	mov    %r15,%rdi
  3d2653:	ff 50 10             	call   *0x10(%rax)
  3d2656:	48 83 3d d2 74 52 00 	cmpq   $0x0,0x5274d2(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d265d:	00 
  3d265e:	0f 84 1d 01 00 00    	je     3d2781 <_ZN5MCLoc11RelocWithPFEv+0x3a51>
  3d2664:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d2669:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d266f:	83 f8 01             	cmp    $0x1,%eax
  3d2672:	75 09                	jne    3d267d <_ZN5MCLoc11RelocWithPFEv+0x394d>
  3d2674:	49 8b 07             	mov    (%r15),%rax
  3d2677:	4c 89 ff             	mov    %r15,%rdi
  3d267a:	ff 50 18             	call   *0x18(%rax)
  3d267d:	48 8b 4c 24 78       	mov    0x78(%rsp),%rcx
  3d2682:	48 85 c9             	test   %rcx,%rcx
  3d2685:	74 0f                	je     3d2696 <_ZN5MCLoc11RelocWithPFEv+0x3966>
  3d2687:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3d268c:	ba 03 00 00 00       	mov    $0x3,%edx
  3d2691:	48 89 fe             	mov    %rdi,%rsi
  3d2694:	ff d1                	call   *%rcx
  3d2696:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d269b:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d26a0:	48 39 c7             	cmp    %rax,%rdi
  3d26a3:	74 05                	je     3d26aa <_ZN5MCLoc11RelocWithPFEv+0x397a>
  3d26a5:	e8 46 d2 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d26aa:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3d26b1:	00 
  3d26b2:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3d26b9:	00 
  3d26ba:	48 39 c7             	cmp    %rax,%rdi
  3d26bd:	74 05                	je     3d26c4 <_ZN5MCLoc11RelocWithPFEv+0x3994>
  3d26bf:	e8 2c d2 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d26c4:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3d26cb:	00 
  3d26cc:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d26d3:	00 
  3d26d4:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d26d8:	48 8b 8c 24 b8 00 00 	mov    0xb8(%rsp),%rcx
  3d26df:	00 
  3d26e0:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d26e7:	00 
  3d26e8:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  3d26ef:	00 
  3d26f0:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d26f7:	00 
  3d26f8:	48 8b 84 24 c8 00 00 	mov    0xc8(%rsp),%rax
  3d26ff:	00 
  3d2700:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d2707:	00 
  3d2708:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d270f:	00 
  3d2710:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d2717:	00 
  3d2718:	48 39 c7             	cmp    %rax,%rdi
  3d271b:	74 05                	je     3d2722 <_ZN5MCLoc11RelocWithPFEv+0x39f2>
  3d271d:	e8 ce d1 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2722:	48 8b 84 24 d0 00 00 	mov    0xd0(%rsp),%rax
  3d2729:	00 
  3d272a:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d2731:	00 
  3d2732:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d2739:	00 
  3d273a:	e8 c1 13 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d273f:	48 8b 84 24 d8 00 00 	mov    0xd8(%rsp),%rax
  3d2746:	00 
  3d2747:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d274e:	00 
  3d274f:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d2753:	48 8b 8c 24 e0 00 00 	mov    0xe0(%rsp),%rcx
  3d275a:	00 
  3d275b:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d2762:	00 
  3d2763:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d276a:	00 00 00 00 00 
  3d276f:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d2776:	00 
  3d2777:	e8 44 5f de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3d277c:	e9 9f 0a 00 00       	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d2781:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d2785:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2788:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d278c:	83 f8 01             	cmp    $0x1,%eax
  3d278f:	0f 85 e8 fe ff ff    	jne    3d267d <_ZN5MCLoc11RelocWithPFEv+0x394d>
  3d2795:	e9 da fe ff ff       	jmp    3d2674 <_ZN5MCLoc11RelocWithPFEv+0x3944>
  3d279a:	48 89 c7             	mov    %rax,%rdi
  3d279d:	e8 5e 09 df ff       	call   1c3100 <__clang_call_terminate>
  3d27a2:	48 89 c7             	mov    %rax,%rdi
  3d27a5:	e8 56 09 df ff       	call   1c3100 <__clang_call_terminate>
  3d27aa:	49 89 c6             	mov    %rax,%r14
  3d27ad:	4d 85 ed             	test   %r13,%r13
  3d27b0:	0f 84 cf 03 00 00    	je     3d2b85 <_ZN5MCLoc11RelocWithPFEv+0x3e55>
  3d27b6:	48 83 3d 72 73 52 00 	cmpq   $0x0,0x527372(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d27bd:	00 
  3d27be:	74 15                	je     3d27d5 <_ZN5MCLoc11RelocWithPFEv+0x3aa5>
  3d27c0:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d27c5:	f0 41 0f c1 45 08    	lock xadd %eax,0x8(%r13)
  3d27cb:	83 f8 01             	cmp    $0x1,%eax
  3d27ce:	74 19                	je     3d27e9 <_ZN5MCLoc11RelocWithPFEv+0x3ab9>
  3d27d0:	e9 b0 03 00 00       	jmp    3d2b85 <_ZN5MCLoc11RelocWithPFEv+0x3e55>
  3d27d5:	41 8b 45 08          	mov    0x8(%r13),%eax
  3d27d9:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d27dc:	41 89 4d 08          	mov    %ecx,0x8(%r13)
  3d27e0:	83 f8 01             	cmp    $0x1,%eax
  3d27e3:	0f 85 9c 03 00 00    	jne    3d2b85 <_ZN5MCLoc11RelocWithPFEv+0x3e55>
  3d27e9:	49 8b 45 00          	mov    0x0(%r13),%rax
  3d27ed:	4c 89 ef             	mov    %r13,%rdi
  3d27f0:	ff 50 10             	call   *0x10(%rax)
  3d27f3:	48 83 3d 35 73 52 00 	cmpq   $0x0,0x527335(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d27fa:	00 
  3d27fb:	74 15                	je     3d2812 <_ZN5MCLoc11RelocWithPFEv+0x3ae2>
  3d27fd:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d2802:	f0 41 0f c1 45 0c    	lock xadd %eax,0xc(%r13)
  3d2808:	83 f8 01             	cmp    $0x1,%eax
  3d280b:	74 19                	je     3d2826 <_ZN5MCLoc11RelocWithPFEv+0x3af6>
  3d280d:	e9 73 03 00 00       	jmp    3d2b85 <_ZN5MCLoc11RelocWithPFEv+0x3e55>
  3d2812:	41 8b 45 0c          	mov    0xc(%r13),%eax
  3d2816:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2819:	41 89 4d 0c          	mov    %ecx,0xc(%r13)
  3d281d:	83 f8 01             	cmp    $0x1,%eax
  3d2820:	0f 85 5f 03 00 00    	jne    3d2b85 <_ZN5MCLoc11RelocWithPFEv+0x3e55>
  3d2826:	49 8b 45 00          	mov    0x0(%r13),%rax
  3d282a:	4c 89 ef             	mov    %r13,%rdi
  3d282d:	ff 50 18             	call   *0x18(%rax)
  3d2830:	e9 50 03 00 00       	jmp    3d2b85 <_ZN5MCLoc11RelocWithPFEv+0x3e55>
  3d2835:	49 89 c6             	mov    %rax,%r14
  3d2838:	e9 ae 03 00 00       	jmp    3d2beb <_ZN5MCLoc11RelocWithPFEv+0x3ebb>
  3d283d:	49 89 c6             	mov    %rax,%r14
  3d2840:	4d 39 ef             	cmp    %r13,%r15
  3d2843:	0f 84 bb 03 00 00    	je     3d2c04 <_ZN5MCLoc11RelocWithPFEv+0x3ed4>
  3d2849:	4c 89 ff             	mov    %r15,%rdi
  3d284c:	e8 9f d0 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2851:	e9 ae 03 00 00       	jmp    3d2c04 <_ZN5MCLoc11RelocWithPFEv+0x3ed4>
  3d2856:	49 89 c6             	mov    %rax,%r14
  3d2859:	e9 ba 03 00 00       	jmp    3d2c18 <_ZN5MCLoc11RelocWithPFEv+0x3ee8>
  3d285e:	49 89 c6             	mov    %rax,%r14
  3d2861:	e9 cc 03 00 00       	jmp    3d2c32 <_ZN5MCLoc11RelocWithPFEv+0x3f02>
  3d2866:	49 89 c6             	mov    %rax,%r14
  3d2869:	e9 c4 03 00 00       	jmp    3d2c32 <_ZN5MCLoc11RelocWithPFEv+0x3f02>
  3d286e:	e9 9f 09 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d2873:	4c 89 f1             	mov    %r14,%rcx
  3d2876:	49 89 c6             	mov    %rax,%r14
  3d2879:	48 8b bc 24 40 01 00 	mov    0x140(%rsp),%rdi
  3d2880:	00 
  3d2881:	48 39 cf             	cmp    %rcx,%rdi
  3d2884:	0f 84 96 09 00 00    	je     3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d288a:	e8 61 d0 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d288f:	e9 8c 09 00 00       	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d2894:	e9 79 09 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d2899:	49 89 c6             	mov    %rax,%r14
  3d289c:	4d 85 e4             	test   %r12,%r12
  3d289f:	0f 84 8f 04 00 00    	je     3d2d34 <_ZN5MCLoc11RelocWithPFEv+0x4004>
  3d28a5:	48 83 3d 83 72 52 00 	cmpq   $0x0,0x527283(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d28ac:	00 
  3d28ad:	74 16                	je     3d28c5 <_ZN5MCLoc11RelocWithPFEv+0x3b95>
  3d28af:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d28b4:	f0 41 0f c1 44 24 08 	lock xadd %eax,0x8(%r12)
  3d28bb:	83 f8 01             	cmp    $0x1,%eax
  3d28be:	74 1b                	je     3d28db <_ZN5MCLoc11RelocWithPFEv+0x3bab>
  3d28c0:	e9 6f 04 00 00       	jmp    3d2d34 <_ZN5MCLoc11RelocWithPFEv+0x4004>
  3d28c5:	41 8b 44 24 08       	mov    0x8(%r12),%eax
  3d28ca:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d28cd:	41 89 4c 24 08       	mov    %ecx,0x8(%r12)
  3d28d2:	83 f8 01             	cmp    $0x1,%eax
  3d28d5:	0f 85 59 04 00 00    	jne    3d2d34 <_ZN5MCLoc11RelocWithPFEv+0x4004>
  3d28db:	49 8b 04 24          	mov    (%r12),%rax
  3d28df:	4c 89 e7             	mov    %r12,%rdi
  3d28e2:	ff 50 10             	call   *0x10(%rax)
  3d28e5:	48 83 3d 43 72 52 00 	cmpq   $0x0,0x527243(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d28ec:	00 
  3d28ed:	74 16                	je     3d2905 <_ZN5MCLoc11RelocWithPFEv+0x3bd5>
  3d28ef:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d28f4:	f0 41 0f c1 44 24 0c 	lock xadd %eax,0xc(%r12)
  3d28fb:	83 f8 01             	cmp    $0x1,%eax
  3d28fe:	74 1b                	je     3d291b <_ZN5MCLoc11RelocWithPFEv+0x3beb>
  3d2900:	e9 2f 04 00 00       	jmp    3d2d34 <_ZN5MCLoc11RelocWithPFEv+0x4004>
  3d2905:	41 8b 44 24 0c       	mov    0xc(%r12),%eax
  3d290a:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d290d:	41 89 4c 24 0c       	mov    %ecx,0xc(%r12)
  3d2912:	83 f8 01             	cmp    $0x1,%eax
  3d2915:	0f 85 19 04 00 00    	jne    3d2d34 <_ZN5MCLoc11RelocWithPFEv+0x4004>
  3d291b:	49 8b 04 24          	mov    (%r12),%rax
  3d291f:	4c 89 e7             	mov    %r12,%rdi
  3d2922:	ff 50 18             	call   *0x18(%rax)
  3d2925:	e9 0a 04 00 00       	jmp    3d2d34 <_ZN5MCLoc11RelocWithPFEv+0x4004>
  3d292a:	49 89 c6             	mov    %rax,%r14
  3d292d:	e9 68 04 00 00       	jmp    3d2d9a <_ZN5MCLoc11RelocWithPFEv+0x406a>
  3d2932:	49 89 c6             	mov    %rax,%r14
  3d2935:	4d 39 ec             	cmp    %r13,%r12
  3d2938:	0f 84 75 04 00 00    	je     3d2db3 <_ZN5MCLoc11RelocWithPFEv+0x4083>
  3d293e:	4c 89 e7             	mov    %r12,%rdi
  3d2941:	e8 aa cf dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2946:	e9 68 04 00 00       	jmp    3d2db3 <_ZN5MCLoc11RelocWithPFEv+0x4083>
  3d294b:	49 89 c6             	mov    %rax,%r14
  3d294e:	e9 74 04 00 00       	jmp    3d2dc7 <_ZN5MCLoc11RelocWithPFEv+0x4097>
  3d2953:	49 89 c6             	mov    %rax,%r14
  3d2956:	e9 86 04 00 00       	jmp    3d2de1 <_ZN5MCLoc11RelocWithPFEv+0x40b1>
  3d295b:	49 89 c6             	mov    %rax,%r14
  3d295e:	e9 7e 04 00 00       	jmp    3d2de1 <_ZN5MCLoc11RelocWithPFEv+0x40b1>
  3d2963:	e9 aa 08 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d2968:	49 89 c6             	mov    %rax,%r14
  3d296b:	48 8b bc 24 40 01 00 	mov    0x140(%rsp),%rdi
  3d2972:	00 
  3d2973:	4c 39 ff             	cmp    %r15,%rdi
  3d2976:	0f 84 a4 08 00 00    	je     3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d297c:	e8 6f cf dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2981:	e9 9a 08 00 00       	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d2986:	49 89 c6             	mov    %rax,%r14
  3d2989:	4d 85 ff             	test   %r15,%r15
  3d298c:	0f 84 51 05 00 00    	je     3d2ee3 <_ZN5MCLoc11RelocWithPFEv+0x41b3>
  3d2992:	48 83 3d 96 71 52 00 	cmpq   $0x0,0x527196(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2999:	00 
  3d299a:	74 15                	je     3d29b1 <_ZN5MCLoc11RelocWithPFEv+0x3c81>
  3d299c:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d29a1:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d29a7:	83 f8 01             	cmp    $0x1,%eax
  3d29aa:	74 19                	je     3d29c5 <_ZN5MCLoc11RelocWithPFEv+0x3c95>
  3d29ac:	e9 32 05 00 00       	jmp    3d2ee3 <_ZN5MCLoc11RelocWithPFEv+0x41b3>
  3d29b1:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d29b5:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d29b8:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d29bc:	83 f8 01             	cmp    $0x1,%eax
  3d29bf:	0f 85 1e 05 00 00    	jne    3d2ee3 <_ZN5MCLoc11RelocWithPFEv+0x41b3>
  3d29c5:	49 8b 07             	mov    (%r15),%rax
  3d29c8:	4c 89 ff             	mov    %r15,%rdi
  3d29cb:	ff 50 10             	call   *0x10(%rax)
  3d29ce:	48 83 3d 5a 71 52 00 	cmpq   $0x0,0x52715a(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d29d5:	00 
  3d29d6:	74 15                	je     3d29ed <_ZN5MCLoc11RelocWithPFEv+0x3cbd>
  3d29d8:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d29dd:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d29e3:	83 f8 01             	cmp    $0x1,%eax
  3d29e6:	74 19                	je     3d2a01 <_ZN5MCLoc11RelocWithPFEv+0x3cd1>
  3d29e8:	e9 f6 04 00 00       	jmp    3d2ee3 <_ZN5MCLoc11RelocWithPFEv+0x41b3>
  3d29ed:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d29f1:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d29f4:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d29f8:	83 f8 01             	cmp    $0x1,%eax
  3d29fb:	0f 85 e2 04 00 00    	jne    3d2ee3 <_ZN5MCLoc11RelocWithPFEv+0x41b3>
  3d2a01:	49 8b 07             	mov    (%r15),%rax
  3d2a04:	4c 89 ff             	mov    %r15,%rdi
  3d2a07:	ff 50 18             	call   *0x18(%rax)
  3d2a0a:	e9 d4 04 00 00       	jmp    3d2ee3 <_ZN5MCLoc11RelocWithPFEv+0x41b3>
  3d2a0f:	49 89 c6             	mov    %rax,%r14
  3d2a12:	4d 85 ed             	test   %r13,%r13
  3d2a15:	0f 84 6f 06 00 00    	je     3d308a <_ZN5MCLoc11RelocWithPFEv+0x435a>
  3d2a1b:	48 83 3d 0d 71 52 00 	cmpq   $0x0,0x52710d(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2a22:	00 
  3d2a23:	74 15                	je     3d2a3a <_ZN5MCLoc11RelocWithPFEv+0x3d0a>
  3d2a25:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d2a2a:	f0 41 0f c1 45 08    	lock xadd %eax,0x8(%r13)
  3d2a30:	83 f8 01             	cmp    $0x1,%eax
  3d2a33:	74 19                	je     3d2a4e <_ZN5MCLoc11RelocWithPFEv+0x3d1e>
  3d2a35:	e9 50 06 00 00       	jmp    3d308a <_ZN5MCLoc11RelocWithPFEv+0x435a>
  3d2a3a:	41 8b 45 08          	mov    0x8(%r13),%eax
  3d2a3e:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2a41:	41 89 4d 08          	mov    %ecx,0x8(%r13)
  3d2a45:	83 f8 01             	cmp    $0x1,%eax
  3d2a48:	0f 85 3c 06 00 00    	jne    3d308a <_ZN5MCLoc11RelocWithPFEv+0x435a>
  3d2a4e:	49 8b 45 00          	mov    0x0(%r13),%rax
  3d2a52:	4c 89 ef             	mov    %r13,%rdi
  3d2a55:	ff 50 10             	call   *0x10(%rax)
  3d2a58:	48 83 3d d0 70 52 00 	cmpq   $0x0,0x5270d0(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2a5f:	00 
  3d2a60:	74 15                	je     3d2a77 <_ZN5MCLoc11RelocWithPFEv+0x3d47>
  3d2a62:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d2a67:	f0 41 0f c1 45 0c    	lock xadd %eax,0xc(%r13)
  3d2a6d:	83 f8 01             	cmp    $0x1,%eax
  3d2a70:	74 19                	je     3d2a8b <_ZN5MCLoc11RelocWithPFEv+0x3d5b>
  3d2a72:	e9 13 06 00 00       	jmp    3d308a <_ZN5MCLoc11RelocWithPFEv+0x435a>
  3d2a77:	41 8b 45 0c          	mov    0xc(%r13),%eax
  3d2a7b:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2a7e:	41 89 4d 0c          	mov    %ecx,0xc(%r13)
  3d2a82:	83 f8 01             	cmp    $0x1,%eax
  3d2a85:	0f 85 ff 05 00 00    	jne    3d308a <_ZN5MCLoc11RelocWithPFEv+0x435a>
  3d2a8b:	49 8b 45 00          	mov    0x0(%r13),%rax
  3d2a8f:	4c 89 ef             	mov    %r13,%rdi
  3d2a92:	ff 50 18             	call   *0x18(%rax)
  3d2a95:	e9 f0 05 00 00       	jmp    3d308a <_ZN5MCLoc11RelocWithPFEv+0x435a>
  3d2a9a:	49 89 c6             	mov    %rax,%r14
  3d2a9d:	e9 a7 04 00 00       	jmp    3d2f49 <_ZN5MCLoc11RelocWithPFEv+0x4219>
  3d2aa2:	49 89 c6             	mov    %rax,%r14
  3d2aa5:	e9 46 06 00 00       	jmp    3d30f0 <_ZN5MCLoc11RelocWithPFEv+0x43c0>
  3d2aaa:	49 89 c6             	mov    %rax,%r14
  3d2aad:	48 8d 84 24 00 01 00 	lea    0x100(%rsp),%rax
  3d2ab4:	00 
  3d2ab5:	49 39 c7             	cmp    %rax,%r15
  3d2ab8:	0f 84 a4 04 00 00    	je     3d2f62 <_ZN5MCLoc11RelocWithPFEv+0x4232>
  3d2abe:	4c 89 ff             	mov    %r15,%rdi
  3d2ac1:	e8 2a ce dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2ac6:	e9 97 04 00 00       	jmp    3d2f62 <_ZN5MCLoc11RelocWithPFEv+0x4232>
  3d2acb:	49 89 c6             	mov    %rax,%r14
  3d2ace:	4d 39 ef             	cmp    %r13,%r15
  3d2ad1:	0f 84 32 06 00 00    	je     3d3109 <_ZN5MCLoc11RelocWithPFEv+0x43d9>
  3d2ad7:	4c 89 ff             	mov    %r15,%rdi
  3d2ada:	e8 11 ce dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2adf:	e9 25 06 00 00       	jmp    3d3109 <_ZN5MCLoc11RelocWithPFEv+0x43d9>
  3d2ae4:	49 89 c6             	mov    %rax,%r14
  3d2ae7:	e9 8a 04 00 00       	jmp    3d2f76 <_ZN5MCLoc11RelocWithPFEv+0x4246>
  3d2aec:	49 89 c6             	mov    %rax,%r14
  3d2aef:	e9 29 06 00 00       	jmp    3d311d <_ZN5MCLoc11RelocWithPFEv+0x43ed>
  3d2af4:	49 89 c6             	mov    %rax,%r14
  3d2af7:	e9 94 04 00 00       	jmp    3d2f90 <_ZN5MCLoc11RelocWithPFEv+0x4260>
  3d2afc:	49 89 c6             	mov    %rax,%r14
  3d2aff:	e9 33 06 00 00       	jmp    3d3137 <_ZN5MCLoc11RelocWithPFEv+0x4407>
  3d2b04:	49 89 c6             	mov    %rax,%r14
  3d2b07:	48 8b bc 24 f0 00 00 	mov    0xf0(%rsp),%rdi
  3d2b0e:	00 
  3d2b0f:	48 8d 84 24 00 01 00 	lea    0x100(%rsp),%rax
  3d2b16:	00 
  3d2b17:	48 39 c7             	cmp    %rax,%rdi
  3d2b1a:	74 12                	je     3d2b2e <_ZN5MCLoc11RelocWithPFEv+0x3dfe>
  3d2b1c:	e8 cf cd dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2b21:	eb 0b                	jmp    3d2b2e <_ZN5MCLoc11RelocWithPFEv+0x3dfe>
  3d2b23:	49 89 c6             	mov    %rax,%r14
  3d2b26:	e9 0c 06 00 00       	jmp    3d3137 <_ZN5MCLoc11RelocWithPFEv+0x4407>
  3d2b2b:	49 89 c6             	mov    %rax,%r14
  3d2b2e:	48 8b 7c 24 68       	mov    0x68(%rsp),%rdi
  3d2b33:	4c 39 ff             	cmp    %r15,%rdi
  3d2b36:	0f 84 54 04 00 00    	je     3d2f90 <_ZN5MCLoc11RelocWithPFEv+0x4260>
  3d2b3c:	e9 4a 04 00 00       	jmp    3d2f8b <_ZN5MCLoc11RelocWithPFEv+0x425b>
  3d2b41:	e9 cc 06 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d2b46:	e9 c7 06 00 00       	jmp    3d3212 <_ZN5MCLoc11RelocWithPFEv+0x44e2>
  3d2b4b:	49 89 c6             	mov    %rax,%r14
  3d2b4e:	48 8b bc 24 40 01 00 	mov    0x140(%rsp),%rdi
  3d2b55:	00 
  3d2b56:	4c 39 ff             	cmp    %r15,%rdi
  3d2b59:	0f 84 c1 06 00 00    	je     3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d2b5f:	e8 8c cd dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2b64:	e9 b7 06 00 00       	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d2b69:	49 89 c6             	mov    %rax,%r14
  3d2b6c:	48 8b 4c 24 38       	mov    0x38(%rsp),%rcx
  3d2b71:	48 85 c9             	test   %rcx,%rcx
  3d2b74:	74 0f                	je     3d2b85 <_ZN5MCLoc11RelocWithPFEv+0x3e55>
  3d2b76:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3d2b7b:	ba 03 00 00 00       	mov    $0x3,%edx
  3d2b80:	48 89 fe             	mov    %rdi,%rsi
  3d2b83:	ff d1                	call   *%rcx
  3d2b85:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3d2b8a:	4d 85 ff             	test   %r15,%r15
  3d2b8d:	74 5c                	je     3d2beb <_ZN5MCLoc11RelocWithPFEv+0x3ebb>
  3d2b8f:	48 83 3d 99 6f 52 00 	cmpq   $0x0,0x526f99(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2b96:	00 
  3d2b97:	74 12                	je     3d2bab <_ZN5MCLoc11RelocWithPFEv+0x3e7b>
  3d2b99:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d2b9e:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d2ba4:	83 f8 01             	cmp    $0x1,%eax
  3d2ba7:	74 12                	je     3d2bbb <_ZN5MCLoc11RelocWithPFEv+0x3e8b>
  3d2ba9:	eb 40                	jmp    3d2beb <_ZN5MCLoc11RelocWithPFEv+0x3ebb>
  3d2bab:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d2baf:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2bb2:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d2bb6:	83 f8 01             	cmp    $0x1,%eax
  3d2bb9:	75 30                	jne    3d2beb <_ZN5MCLoc11RelocWithPFEv+0x3ebb>
  3d2bbb:	49 8b 07             	mov    (%r15),%rax
  3d2bbe:	4c 89 ff             	mov    %r15,%rdi
  3d2bc1:	ff 50 10             	call   *0x10(%rax)
  3d2bc4:	48 83 3d 64 6f 52 00 	cmpq   $0x0,0x526f64(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2bcb:	00 
  3d2bcc:	0f 84 1d 01 00 00    	je     3d2cef <_ZN5MCLoc11RelocWithPFEv+0x3fbf>
  3d2bd2:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d2bd7:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d2bdd:	83 f8 01             	cmp    $0x1,%eax
  3d2be0:	75 09                	jne    3d2beb <_ZN5MCLoc11RelocWithPFEv+0x3ebb>
  3d2be2:	49 8b 07             	mov    (%r15),%rax
  3d2be5:	4c 89 ff             	mov    %r15,%rdi
  3d2be8:	ff 50 18             	call   *0x18(%rax)
  3d2beb:	48 8b 4c 24 78       	mov    0x78(%rsp),%rcx
  3d2bf0:	48 85 c9             	test   %rcx,%rcx
  3d2bf3:	74 0f                	je     3d2c04 <_ZN5MCLoc11RelocWithPFEv+0x3ed4>
  3d2bf5:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3d2bfa:	ba 03 00 00 00       	mov    $0x3,%edx
  3d2bff:	48 89 fe             	mov    %rdi,%rsi
  3d2c02:	ff d1                	call   *%rcx
  3d2c04:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d2c09:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d2c0e:	48 39 c7             	cmp    %rax,%rdi
  3d2c11:	74 05                	je     3d2c18 <_ZN5MCLoc11RelocWithPFEv+0x3ee8>
  3d2c13:	e8 d8 cc dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2c18:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3d2c1f:	00 
  3d2c20:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3d2c27:	00 
  3d2c28:	48 39 c7             	cmp    %rax,%rdi
  3d2c2b:	74 05                	je     3d2c32 <_ZN5MCLoc11RelocWithPFEv+0x3f02>
  3d2c2d:	e8 be cc dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2c32:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  3d2c39:	00 
  3d2c3a:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d2c41:	00 
  3d2c42:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d2c46:	48 8b 8c 24 b8 00 00 	mov    0xb8(%rsp),%rcx
  3d2c4d:	00 
  3d2c4e:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d2c55:	00 
  3d2c56:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  3d2c5d:	00 
  3d2c5e:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d2c65:	00 
  3d2c66:	48 8b 84 24 c8 00 00 	mov    0xc8(%rsp),%rax
  3d2c6d:	00 
  3d2c6e:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d2c75:	00 
  3d2c76:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d2c7d:	00 
  3d2c7e:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d2c85:	00 
  3d2c86:	48 39 c7             	cmp    %rax,%rdi
  3d2c89:	74 05                	je     3d2c90 <_ZN5MCLoc11RelocWithPFEv+0x3f60>
  3d2c8b:	e8 60 cc dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2c90:	48 8b 84 24 d0 00 00 	mov    0xd0(%rsp),%rax
  3d2c97:	00 
  3d2c98:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d2c9f:	00 
  3d2ca0:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d2ca7:	00 
  3d2ca8:	e8 53 0e de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d2cad:	48 8b 84 24 d8 00 00 	mov    0xd8(%rsp),%rax
  3d2cb4:	00 
  3d2cb5:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d2cbc:	00 
  3d2cbd:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d2cc1:	48 8b 8c 24 e0 00 00 	mov    0xe0(%rsp),%rcx
  3d2cc8:	00 
  3d2cc9:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d2cd0:	00 
  3d2cd1:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d2cd8:	00 00 00 00 00 
  3d2cdd:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d2ce4:	00 
  3d2ce5:	e8 d6 59 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3d2cea:	e9 31 05 00 00       	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d2cef:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d2cf3:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2cf6:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d2cfa:	83 f8 01             	cmp    $0x1,%eax
  3d2cfd:	0f 85 e8 fe ff ff    	jne    3d2beb <_ZN5MCLoc11RelocWithPFEv+0x3ebb>
  3d2d03:	e9 da fe ff ff       	jmp    3d2be2 <_ZN5MCLoc11RelocWithPFEv+0x3eb2>
  3d2d08:	48 89 c7             	mov    %rax,%rdi
  3d2d0b:	e8 f0 03 df ff       	call   1c3100 <__clang_call_terminate>
  3d2d10:	48 89 c7             	mov    %rax,%rdi
  3d2d13:	e8 e8 03 df ff       	call   1c3100 <__clang_call_terminate>
  3d2d18:	49 89 c6             	mov    %rax,%r14
  3d2d1b:	48 8b 4c 24 38       	mov    0x38(%rsp),%rcx
  3d2d20:	48 85 c9             	test   %rcx,%rcx
  3d2d23:	74 0f                	je     3d2d34 <_ZN5MCLoc11RelocWithPFEv+0x4004>
  3d2d25:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3d2d2a:	ba 03 00 00 00       	mov    $0x3,%edx
  3d2d2f:	48 89 fe             	mov    %rdi,%rsi
  3d2d32:	ff d1                	call   *%rcx
  3d2d34:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3d2d39:	4d 85 ff             	test   %r15,%r15
  3d2d3c:	74 5c                	je     3d2d9a <_ZN5MCLoc11RelocWithPFEv+0x406a>
  3d2d3e:	48 83 3d ea 6d 52 00 	cmpq   $0x0,0x526dea(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2d45:	00 
  3d2d46:	74 12                	je     3d2d5a <_ZN5MCLoc11RelocWithPFEv+0x402a>
  3d2d48:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d2d4d:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d2d53:	83 f8 01             	cmp    $0x1,%eax
  3d2d56:	74 12                	je     3d2d6a <_ZN5MCLoc11RelocWithPFEv+0x403a>
  3d2d58:	eb 40                	jmp    3d2d9a <_ZN5MCLoc11RelocWithPFEv+0x406a>
  3d2d5a:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d2d5e:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2d61:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d2d65:	83 f8 01             	cmp    $0x1,%eax
  3d2d68:	75 30                	jne    3d2d9a <_ZN5MCLoc11RelocWithPFEv+0x406a>
  3d2d6a:	49 8b 07             	mov    (%r15),%rax
  3d2d6d:	4c 89 ff             	mov    %r15,%rdi
  3d2d70:	ff 50 10             	call   *0x10(%rax)
  3d2d73:	48 83 3d b5 6d 52 00 	cmpq   $0x0,0x526db5(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2d7a:	00 
  3d2d7b:	0f 84 1d 01 00 00    	je     3d2e9e <_ZN5MCLoc11RelocWithPFEv+0x416e>
  3d2d81:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d2d86:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d2d8c:	83 f8 01             	cmp    $0x1,%eax
  3d2d8f:	75 09                	jne    3d2d9a <_ZN5MCLoc11RelocWithPFEv+0x406a>
  3d2d91:	49 8b 07             	mov    (%r15),%rax
  3d2d94:	4c 89 ff             	mov    %r15,%rdi
  3d2d97:	ff 50 18             	call   *0x18(%rax)
  3d2d9a:	48 8b 4c 24 78       	mov    0x78(%rsp),%rcx
  3d2d9f:	48 85 c9             	test   %rcx,%rcx
  3d2da2:	74 0f                	je     3d2db3 <_ZN5MCLoc11RelocWithPFEv+0x4083>
  3d2da4:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3d2da9:	ba 03 00 00 00       	mov    $0x3,%edx
  3d2dae:	48 89 fe             	mov    %rdi,%rsi
  3d2db1:	ff d1                	call   *%rcx
  3d2db3:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d2db8:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d2dbd:	48 39 c7             	cmp    %rax,%rdi
  3d2dc0:	74 05                	je     3d2dc7 <_ZN5MCLoc11RelocWithPFEv+0x4097>
  3d2dc2:	e8 29 cb dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2dc7:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3d2dce:	00 
  3d2dcf:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3d2dd6:	00 
  3d2dd7:	48 39 c7             	cmp    %rax,%rdi
  3d2dda:	74 05                	je     3d2de1 <_ZN5MCLoc11RelocWithPFEv+0x40b1>
  3d2ddc:	e8 0f cb dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2de1:	48 8b 84 24 e0 00 00 	mov    0xe0(%rsp),%rax
  3d2de8:	00 
  3d2de9:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d2df0:	00 
  3d2df1:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d2df5:	48 8b 8c 24 d8 00 00 	mov    0xd8(%rsp),%rcx
  3d2dfc:	00 
  3d2dfd:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d2e04:	00 
  3d2e05:	48 8b 84 24 d0 00 00 	mov    0xd0(%rsp),%rax
  3d2e0c:	00 
  3d2e0d:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d2e14:	00 
  3d2e15:	48 8b 84 24 c8 00 00 	mov    0xc8(%rsp),%rax
  3d2e1c:	00 
  3d2e1d:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d2e24:	00 
  3d2e25:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d2e2c:	00 
  3d2e2d:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d2e34:	00 
  3d2e35:	48 39 c7             	cmp    %rax,%rdi
  3d2e38:	74 05                	je     3d2e3f <_ZN5MCLoc11RelocWithPFEv+0x410f>
  3d2e3a:	e8 b1 ca dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2e3f:	48 8b 84 24 b8 00 00 	mov    0xb8(%rsp),%rax
  3d2e46:	00 
  3d2e47:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d2e4e:	00 
  3d2e4f:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d2e56:	00 
  3d2e57:	e8 a4 0c de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d2e5c:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  3d2e63:	00 
  3d2e64:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d2e6b:	00 
  3d2e6c:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d2e70:	48 8b 8c 24 b0 00 00 	mov    0xb0(%rsp),%rcx
  3d2e77:	00 
  3d2e78:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d2e7f:	00 
  3d2e80:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d2e87:	00 00 00 00 00 
  3d2e8c:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d2e93:	00 
  3d2e94:	e8 27 58 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3d2e99:	e9 82 03 00 00       	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d2e9e:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d2ea2:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2ea5:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d2ea9:	83 f8 01             	cmp    $0x1,%eax
  3d2eac:	0f 85 e8 fe ff ff    	jne    3d2d9a <_ZN5MCLoc11RelocWithPFEv+0x406a>
  3d2eb2:	e9 da fe ff ff       	jmp    3d2d91 <_ZN5MCLoc11RelocWithPFEv+0x4061>
  3d2eb7:	48 89 c7             	mov    %rax,%rdi
  3d2eba:	e8 41 02 df ff       	call   1c3100 <__clang_call_terminate>
  3d2ebf:	48 89 c7             	mov    %rax,%rdi
  3d2ec2:	e8 39 02 df ff       	call   1c3100 <__clang_call_terminate>
  3d2ec7:	49 89 c6             	mov    %rax,%r14
  3d2eca:	48 8b 4c 24 38       	mov    0x38(%rsp),%rcx
  3d2ecf:	48 85 c9             	test   %rcx,%rcx
  3d2ed2:	74 0f                	je     3d2ee3 <_ZN5MCLoc11RelocWithPFEv+0x41b3>
  3d2ed4:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3d2ed9:	ba 03 00 00 00       	mov    $0x3,%edx
  3d2ede:	48 89 fe             	mov    %rdi,%rsi
  3d2ee1:	ff d1                	call   *%rcx
  3d2ee3:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3d2ee8:	4d 85 ff             	test   %r15,%r15
  3d2eeb:	74 5c                	je     3d2f49 <_ZN5MCLoc11RelocWithPFEv+0x4219>
  3d2eed:	48 83 3d 3b 6c 52 00 	cmpq   $0x0,0x526c3b(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2ef4:	00 
  3d2ef5:	74 12                	je     3d2f09 <_ZN5MCLoc11RelocWithPFEv+0x41d9>
  3d2ef7:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d2efc:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d2f02:	83 f8 01             	cmp    $0x1,%eax
  3d2f05:	74 12                	je     3d2f19 <_ZN5MCLoc11RelocWithPFEv+0x41e9>
  3d2f07:	eb 40                	jmp    3d2f49 <_ZN5MCLoc11RelocWithPFEv+0x4219>
  3d2f09:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d2f0d:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d2f10:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d2f14:	83 f8 01             	cmp    $0x1,%eax
  3d2f17:	75 30                	jne    3d2f49 <_ZN5MCLoc11RelocWithPFEv+0x4219>
  3d2f19:	49 8b 07             	mov    (%r15),%rax
  3d2f1c:	4c 89 ff             	mov    %r15,%rdi
  3d2f1f:	ff 50 10             	call   *0x10(%rax)
  3d2f22:	48 83 3d 06 6c 52 00 	cmpq   $0x0,0x526c06(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d2f29:	00 
  3d2f2a:	0f 84 15 01 00 00    	je     3d3045 <_ZN5MCLoc11RelocWithPFEv+0x4315>
  3d2f30:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d2f35:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d2f3b:	83 f8 01             	cmp    $0x1,%eax
  3d2f3e:	75 09                	jne    3d2f49 <_ZN5MCLoc11RelocWithPFEv+0x4219>
  3d2f40:	49 8b 07             	mov    (%r15),%rax
  3d2f43:	4c 89 ff             	mov    %r15,%rdi
  3d2f46:	ff 50 18             	call   *0x18(%rax)
  3d2f49:	48 8b 4c 24 78       	mov    0x78(%rsp),%rcx
  3d2f4e:	48 85 c9             	test   %rcx,%rcx
  3d2f51:	74 0f                	je     3d2f62 <_ZN5MCLoc11RelocWithPFEv+0x4232>
  3d2f53:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3d2f58:	ba 03 00 00 00       	mov    $0x3,%edx
  3d2f5d:	48 89 fe             	mov    %rdi,%rsi
  3d2f60:	ff d1                	call   *%rcx
  3d2f62:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d2f67:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d2f6c:	48 39 c7             	cmp    %rax,%rdi
  3d2f6f:	74 05                	je     3d2f76 <_ZN5MCLoc11RelocWithPFEv+0x4246>
  3d2f71:	e8 7a c9 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2f76:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3d2f7d:	00 
  3d2f7e:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3d2f85:	00 
  3d2f86:	48 39 c7             	cmp    %rax,%rdi
  3d2f89:	74 05                	je     3d2f90 <_ZN5MCLoc11RelocWithPFEv+0x4260>
  3d2f8b:	e8 60 c9 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2f90:	4c 8b 3d 31 7b 52 00 	mov    0x527b31(%rip),%r15        # 8faac8 <_ZTTNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3d2f97:	49 8b 07             	mov    (%r15),%rax
  3d2f9a:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d2fa1:	00 
  3d2fa2:	49 8b 4f 40          	mov    0x40(%r15),%rcx
  3d2fa6:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d2faa:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d2fb1:	00 
  3d2fb2:	49 8b 47 48          	mov    0x48(%r15),%rax
  3d2fb6:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d2fbd:	00 
  3d2fbe:	48 8b 05 2b 43 52 00 	mov    0x52432b(%rip),%rax        # 8f72f0 <_ZTVNSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3d2fc5:	48 83 c0 10          	add    $0x10,%rax
  3d2fc9:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d2fd0:	00 
  3d2fd1:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d2fd8:	00 
  3d2fd9:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d2fe0:	00 
  3d2fe1:	48 39 c7             	cmp    %rax,%rdi
  3d2fe4:	74 05                	je     3d2feb <_ZN5MCLoc11RelocWithPFEv+0x42bb>
  3d2fe6:	e8 05 c9 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d2feb:	48 8b 05 5e 5a 52 00 	mov    0x525a5e(%rip),%rax        # 8f8a50 <_ZTVSt15basic_streambufIcSt11char_traitsIcEE@GLIBCXX_3.4>
  3d2ff2:	48 83 c0 10          	add    $0x10,%rax
  3d2ff6:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d2ffd:	00 
  3d2ffe:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d3005:	00 
  3d3006:	e8 f5 0a de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d300b:	49 8b 47 10          	mov    0x10(%r15),%rax
  3d300f:	49 8b 4f 18          	mov    0x18(%r15),%rcx
  3d3013:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d301a:	00 
  3d301b:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d301f:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d3026:	00 
  3d3027:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d302e:	00 00 00 00 00 
  3d3033:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d303a:	00 
  3d303b:	e8 80 56 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3d3040:	e9 db 01 00 00       	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d3045:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d3049:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d304c:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d3050:	83 f8 01             	cmp    $0x1,%eax
  3d3053:	0f 85 f0 fe ff ff    	jne    3d2f49 <_ZN5MCLoc11RelocWithPFEv+0x4219>
  3d3059:	e9 e2 fe ff ff       	jmp    3d2f40 <_ZN5MCLoc11RelocWithPFEv+0x4210>
  3d305e:	48 89 c7             	mov    %rax,%rdi
  3d3061:	e8 9a 00 df ff       	call   1c3100 <__clang_call_terminate>
  3d3066:	48 89 c7             	mov    %rax,%rdi
  3d3069:	e8 92 00 df ff       	call   1c3100 <__clang_call_terminate>
  3d306e:	49 89 c6             	mov    %rax,%r14
  3d3071:	48 8b 4c 24 38       	mov    0x38(%rsp),%rcx
  3d3076:	48 85 c9             	test   %rcx,%rcx
  3d3079:	74 0f                	je     3d308a <_ZN5MCLoc11RelocWithPFEv+0x435a>
  3d307b:	48 8d 7c 24 28       	lea    0x28(%rsp),%rdi
  3d3080:	ba 03 00 00 00       	mov    $0x3,%edx
  3d3085:	48 89 fe             	mov    %rdi,%rsi
  3d3088:	ff d1                	call   *%rcx
  3d308a:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  3d308f:	4d 85 ff             	test   %r15,%r15
  3d3092:	74 5c                	je     3d30f0 <_ZN5MCLoc11RelocWithPFEv+0x43c0>
  3d3094:	48 83 3d 94 6a 52 00 	cmpq   $0x0,0x526a94(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d309b:	00 
  3d309c:	74 12                	je     3d30b0 <_ZN5MCLoc11RelocWithPFEv+0x4380>
  3d309e:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d30a3:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
  3d30a9:	83 f8 01             	cmp    $0x1,%eax
  3d30ac:	74 12                	je     3d30c0 <_ZN5MCLoc11RelocWithPFEv+0x4390>
  3d30ae:	eb 40                	jmp    3d30f0 <_ZN5MCLoc11RelocWithPFEv+0x43c0>
  3d30b0:	41 8b 47 08          	mov    0x8(%r15),%eax
  3d30b4:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d30b7:	41 89 4f 08          	mov    %ecx,0x8(%r15)
  3d30bb:	83 f8 01             	cmp    $0x1,%eax
  3d30be:	75 30                	jne    3d30f0 <_ZN5MCLoc11RelocWithPFEv+0x43c0>
  3d30c0:	49 8b 07             	mov    (%r15),%rax
  3d30c3:	4c 89 ff             	mov    %r15,%rdi
  3d30c6:	ff 50 10             	call   *0x10(%rax)
  3d30c9:	48 83 3d 5f 6a 52 00 	cmpq   $0x0,0x526a5f(%rip)        # 8f9b30 <__pthread_key_create@GLIBC_2.2.5>
  3d30d0:	00 
  3d30d1:	0f 84 12 01 00 00    	je     3d31e9 <_ZN5MCLoc11RelocWithPFEv+0x44b9>
  3d30d7:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  3d30dc:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
  3d30e2:	83 f8 01             	cmp    $0x1,%eax
  3d30e5:	75 09                	jne    3d30f0 <_ZN5MCLoc11RelocWithPFEv+0x43c0>
  3d30e7:	49 8b 07             	mov    (%r15),%rax
  3d30ea:	4c 89 ff             	mov    %r15,%rdi
  3d30ed:	ff 50 18             	call   *0x18(%rax)
  3d30f0:	48 8b 4c 24 78       	mov    0x78(%rsp),%rcx
  3d30f5:	48 85 c9             	test   %rcx,%rcx
  3d30f8:	74 0f                	je     3d3109 <_ZN5MCLoc11RelocWithPFEv+0x43d9>
  3d30fa:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
  3d30ff:	ba 03 00 00 00       	mov    $0x3,%edx
  3d3104:	48 89 fe             	mov    %rdi,%rsi
  3d3107:	ff d1                	call   *%rcx
  3d3109:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
  3d310e:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  3d3113:	48 39 c7             	cmp    %rax,%rdi
  3d3116:	74 05                	je     3d311d <_ZN5MCLoc11RelocWithPFEv+0x43ed>
  3d3118:	e8 d3 c7 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d311d:	48 8b bc 24 90 00 00 	mov    0x90(%rsp),%rdi
  3d3124:	00 
  3d3125:	48 8d 84 24 a0 00 00 	lea    0xa0(%rsp),%rax
  3d312c:	00 
  3d312d:	48 39 c7             	cmp    %rax,%rdi
  3d3130:	74 05                	je     3d3137 <_ZN5MCLoc11RelocWithPFEv+0x4407>
  3d3132:	e8 b9 c7 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d3137:	4c 8b 3d 8a 79 52 00 	mov    0x52798a(%rip),%r15        # 8faac8 <_ZTTNSt7__cxx1118basic_stringstreamIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3d313e:	49 8b 07             	mov    (%r15),%rax
  3d3141:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d3148:	00 
  3d3149:	49 8b 4f 40          	mov    0x40(%r15),%rcx
  3d314d:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d3151:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d3158:	00 
  3d3159:	49 8b 47 48          	mov    0x48(%r15),%rax
  3d315d:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  3d3164:	00 
  3d3165:	48 8b 05 84 41 52 00 	mov    0x524184(%rip),%rax        # 8f72f0 <_ZTVNSt7__cxx1115basic_stringbufIcSt11char_traitsIcESaIcEEE@GLIBCXX_3.4.21>
  3d316c:	48 83 c0 10          	add    $0x10,%rax
  3d3170:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d3177:	00 
  3d3178:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  3d317f:	00 
  3d3180:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  3d3187:	00 
  3d3188:	48 39 c7             	cmp    %rax,%rdi
  3d318b:	74 05                	je     3d3192 <_ZN5MCLoc11RelocWithPFEv+0x4462>
  3d318d:	e8 5e c7 dd ff       	call   1af8f0 <_ZdlPv@plt>
  3d3192:	48 8b 05 b7 58 52 00 	mov    0x5258b7(%rip),%rax        # 8f8a50 <_ZTVSt15basic_streambufIcSt11char_traitsIcEE@GLIBCXX_3.4>
  3d3199:	48 83 c0 10          	add    $0x10,%rax
  3d319d:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  3d31a4:	00 
  3d31a5:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  3d31ac:	00 
  3d31ad:	e8 4e 09 de ff       	call   1b3b00 <_ZNSt6localeD1Ev@plt>
  3d31b2:	49 8b 47 10          	mov    0x10(%r15),%rax
  3d31b6:	49 8b 4f 18          	mov    0x18(%r15),%rcx
  3d31ba:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  3d31c1:	00 
  3d31c2:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  3d31c6:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  3d31cd:	00 
  3d31ce:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  3d31d5:	00 00 00 00 00 
  3d31da:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  3d31e1:	00 
  3d31e2:	e8 d9 54 de ff       	call   1b86c0 <_ZNSt8ios_baseD2Ev@plt>
  3d31e7:	eb 37                	jmp    3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d31e9:	41 8b 47 0c          	mov    0xc(%r15),%eax
  3d31ed:	8d 48 ff             	lea    -0x1(%rax),%ecx
  3d31f0:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
  3d31f4:	83 f8 01             	cmp    $0x1,%eax
  3d31f7:	0f 85 f3 fe ff ff    	jne    3d30f0 <_ZN5MCLoc11RelocWithPFEv+0x43c0>
  3d31fd:	e9 e5 fe ff ff       	jmp    3d30e7 <_ZN5MCLoc11RelocWithPFEv+0x43b7>
  3d3202:	48 89 c7             	mov    %rax,%rdi
  3d3205:	e8 f6 fe de ff       	call   1c3100 <__clang_call_terminate>
  3d320a:	48 89 c7             	mov    %rax,%rdi
  3d320d:	e8 ee fe de ff       	call   1c3100 <__clang_call_terminate>
  3d3212:	49 89 c6             	mov    %rax,%r14
  3d3215:	66 66 2e 0f 1f 84 00 	data16 cs nopw 0x0(%rax,%rax,1)
  3d321c:	00 00 00 00 
  3d3220:	48 89 df             	mov    %rbx,%rdi
  3d3223:	e8 88 43 de ff       	call   1b75b0 <pthread_mutex_unlock@plt>
  3d3228:	83 f8 04             	cmp    $0x4,%eax
  3d322b:	74 f3                	je     3d3220 <_ZN5MCLoc11RelocWithPFEv+0x44f0>
  3d322d:	4c 89 f7             	mov    %r14,%rdi
  3d3230:	e8 5b 26 de ff       	call   1b5890 <_Unwind_Resume@plt>
  3d3235:	66 66 2e 0f 1f 84 00 	data16 cs nopw 0x0(%rax,%rax,1)
  3d323c:	00 00 00 00 
