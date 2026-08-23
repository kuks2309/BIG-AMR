
/media/amap/6ab6980d-f090-4387-8753-a2251e75651d/usr/local/SeerRobotics/rbk/plugins/libOdoCalculator.so:     file format elf64-x86-64


Disassembly of section .text:

000000000015d490 <AbstractOdometer::CalPose()>:
AbstractOdometer::CalPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:425
  15d490:	55                   	push   %rbp
  15d491:	48 89 e5             	mov    %rsp,%rbp
  15d494:	41 57                	push   %r15
  15d496:	41 56                	push   %r14
  15d498:	41 55                	push   %r13
  15d49a:	41 54                	push   %r12
  15d49c:	53                   	push   %rbx
  15d49d:	48 83 e4 f0          	and    $0xfffffffffffffff0,%rsp
  15d4a1:	48 81 ec 90 02 00 00 	sub    $0x290,%rsp
  15d4a8:	49 89 fc             	mov    %rdi,%r12
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:428
  15d4ab:	41 80 7c 24 0b 00    	cmpb   $0x0,0xb(%r12)
  15d4b1:	0f 84 f8 05 00 00    	je     15daaf <AbstractOdometer::CalPose()+0x61f>
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:437
  15d4b7:	41 80 7c 24 0d 00    	cmpb   $0x0,0xd(%r12)
  15d4bd:	0f 84 05 01 00 00    	je     15d5c8 <AbstractOdometer::CalPose()+0x138>
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:438
  15d4c3:	f2 41 0f 10 84 24 f0 	movsd  0xf0(%r12),%xmm0
  15d4ca:	00 00 00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:439
  15d4cd:	0f 29 84 24 d0 00 00 	movaps %xmm0,0xd0(%rsp)
  15d4d4:	00 
  15d4d5:	f2 41 0f 10 84 24 f8 	movsd  0xf8(%r12),%xmm0
  15d4dc:	00 00 00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:440
  15d4df:	0f 29 84 24 e0 00 00 	movaps %xmm0,0xe0(%rsp)
  15d4e6:	00 
  15d4e7:	f2 41 0f 10 84 24 00 	movsd  0x100(%r12),%xmm0
  15d4ee:	01 00 00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:441
  15d4f1:	41 80 7c 24 0c 00    	cmpb   $0x0,0xc(%r12)
  15d4f7:	0f 84 13 05 00 00    	je     15da10 <AbstractOdometer::CalPose()+0x580>
  15d4fd:	66 0f 29 84 24 a0 00 	movapd %xmm0,0xa0(%rsp)
  15d504:	00 00 
  15d506:	48 8d bc 24 00 01 00 	lea    0x100(%rsp),%rdi
  15d50d:	00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:442
  15d50e:	be 18 00 00 00       	mov    $0x18,%esi
  15d513:	e8 b8 6f f2 ff       	call   844d0 <std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::basic_stringstream(std::_Ios_Openmode)@plt>
  15d518:	48 8d bc 24 10 01 00 	lea    0x110(%rsp),%rdi
  15d51f:	00 
std::basic_ostream<char, std::char_traits<char> >& std::operator<< <std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ostream:561
  15d520:	48 8d 35 bd 62 04 00 	lea    0x462bd(%rip),%rsi        # 1a37e4 <typeinfo name for rbk::Logger::Thread::move2thread<AbstractOdometer::LogErrorStr(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >)::$_13>(AbstractOdometer::LogErrorStr(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >)::$_13&&)::{lambda()#1}+0x554>
  15d527:	ba 32 00 00 00       	mov    $0x32,%edx
  15d52c:	e8 8f 8c f2 ff       	call   861c0 <std::basic_ostream<char, std::char_traits<char> >& std::__ostream_insert<char, std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*, long)@plt>
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::str() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:779
  15d531:	48 8d b4 24 18 01 00 	lea    0x118(%rsp),%rsi
  15d538:	00 
  15d539:	48 8d bc 24 b0 00 00 	lea    0xb0(%rsp),%rdi
  15d540:	00 
  15d541:	e8 ba 6d f2 ff       	call   84300 <std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::str() const@plt>
AbstractOdometer::CalPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:442
  15d546:	e8 95 69 f2 ff       	call   83ee0 <rbk::Logger::thread()@plt>
  15d54b:	49 89 c6             	mov    %rax,%r14
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:182
  15d54e:	48 8d 54 24 18       	lea    0x18(%rsp),%rdx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  15d553:	48 89 54 24 08       	mov    %rdx,0x8(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  15d558:	4c 8b bc 24 b0 00 00 	mov    0xb0(%rsp),%r15
  15d55f:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  15d560:	48 8b 9c 24 b8 00 00 	mov    0xb8(%rsp),%rbx
  15d567:	00 
bool __gnu_cxx::__is_null_pointer<char>(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/type_traits.h:153
  15d568:	4d 85 ff             	test   %r15,%r15
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:211
  15d56b:	75 09                	jne    15d576 <AbstractOdometer::CalPose()+0xe6>
  15d56d:	48 85 db             	test   %rbx,%rbx
  15d570:	0f 85 4a 05 00 00    	jne    15dac0 <AbstractOdometer::CalPose()+0x630>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:215
  15d576:	48 89 5c 24 38       	mov    %rbx,0x38(%rsp)
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:217
  15d57b:	48 83 fb 0f          	cmp    $0xf,%rbx
  15d57f:	0f 86 b6 00 00 00    	jbe    15d63b <AbstractOdometer::CalPose()+0x1ab>
AbstractOdometer::CalPose():
  15d585:	49 89 d5             	mov    %rdx,%r13
  15d588:	48 8d 7c 24 08       	lea    0x8(%rsp),%rdi
  15d58d:	48 8d 74 24 38       	lea    0x38(%rsp),%rsi
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:219
  15d592:	31 d2                	xor    %edx,%edx
  15d594:	e8 97 7b f2 ff       	call   85130 <std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_create(unsigned long&, unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  15d599:	48 89 44 24 08       	mov    %rax,0x8(%rsp)
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:220
  15d59e:	48 8b 4c 24 38       	mov    0x38(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  15d5a3:	48 89 4c 24 18       	mov    %rcx,0x18(%rsp)
  15d5a8:	4c 89 ea             	mov    %r13,%rdx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  15d5ab:	48 85 db             	test   %rbx,%rbx
  15d5ae:	0f 84 a9 00 00 00    	je     15d65d <AbstractOdometer::CalPose()+0x1cd>
  15d5b4:	48 83 fb 01          	cmp    $0x1,%rbx
  15d5b8:	0f 85 8b 00 00 00    	jne    15d649 <AbstractOdometer::CalPose()+0x1b9>
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  15d5be:	41 8a 0f             	mov    (%r15),%cl
  15d5c1:	88 08                	mov    %cl,(%rax)
  15d5c3:	e9 95 00 00 00       	jmp    15d65d <AbstractOdometer::CalPose()+0x1cd>
AbstractOdometer::CalPose():
  15d5c8:	49 8b 84 24 b8 00 00 	mov    0xb8(%r12),%rax
  15d5cf:	00 
  15d5d0:	49 2b 84 24 c0 00 00 	sub    0xc0(%r12),%rax
  15d5d7:	00 
  15d5d8:	66 48 0f 6e c8       	movq   %rax,%xmm1
  15d5dd:	66 0f 62 0d cb ea 03 	punpckldq 0x3eacb(%rip),%xmm1        # 19c0b0 <typeinfo name for FollowErrorAndResponseMonitor+0x30>
  15d5e4:	00 
  15d5e5:	66 0f 5c 0d d3 ea 03 	subpd  0x3ead3(%rip),%xmm1        # 19c0c0 <typeinfo name for FollowErrorAndResponseMonitor+0x40>
  15d5ec:	00 
  15d5ed:	66 0f 70 c1 4e       	pshufd $0x4e,%xmm1,%xmm0
  15d5f2:	66 0f 58 c1          	addpd  %xmm1,%xmm0
  15d5f6:	f2 0f 5e 05 a2 ea 03 	divsd  0x3eaa2(%rip),%xmm0        # 19c0a0 <typeinfo name for FollowErrorAndResponseMonitor+0x20>
  15d5fd:	00 
  15d5fe:	f2 41 0f 10 8c 24 d8 	movsd  0xd8(%r12),%xmm1
  15d605:	00 00 00 
  15d608:	f2 0f 59 c8          	mulsd  %xmm0,%xmm1
  15d60c:	66 0f 29 8c 24 d0 00 	movapd %xmm1,0xd0(%rsp)
  15d613:	00 00 
  15d615:	f2 41 0f 10 8c 24 e0 	movsd  0xe0(%r12),%xmm1
  15d61c:	00 00 00 
  15d61f:	f2 0f 59 c8          	mulsd  %xmm0,%xmm1
  15d623:	66 0f 29 8c 24 e0 00 	movapd %xmm1,0xe0(%rsp)
  15d62a:	00 00 
  15d62c:	f2 41 0f 59 84 24 e8 	mulsd  0xe8(%r12),%xmm0
  15d633:	00 00 00 
  15d636:	e9 d5 03 00 00       	jmp    15da10 <AbstractOdometer::CalPose()+0x580>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  15d63b:	48 89 d0             	mov    %rdx,%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  15d63e:	48 85 db             	test   %rbx,%rbx
  15d641:	0f 85 6d ff ff ff    	jne    15d5b4 <AbstractOdometer::CalPose()+0x124>
  15d647:	eb 14                	jmp    15d65d <AbstractOdometer::CalPose()+0x1cd>
AbstractOdometer::CalPose():
  15d649:	49 89 d5             	mov    %rdx,%r13
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  15d64c:	48 89 c7             	mov    %rax,%rdi
  15d64f:	4c 89 fe             	mov    %r15,%rsi
  15d652:	48 89 da             	mov    %rbx,%rdx
  15d655:	e8 16 5e f2 ff       	call   83470 <memcpy@plt>
  15d65a:	4c 89 ea             	mov    %r13,%rdx
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:232
  15d65d:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  15d662:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  15d667:	48 8b 4c 24 08       	mov    0x8(%rsp),%rcx
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  15d66c:	c6 04 01 00          	movb   $0x0,(%rcx,%rax,1)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:182
  15d670:	4c 8d 7c 24 48       	lea    0x48(%rsp),%r15
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  15d675:	4c 89 7c 24 38       	mov    %r15,0x38(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  15d67a:	48 8b 5c 24 08       	mov    0x8(%rsp),%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  15d67f:	48 39 d3             	cmp    %rdx,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:534
  15d682:	74 11                	je     15d695 <AbstractOdometer::CalPose()+0x205>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  15d684:	48 89 5c 24 38       	mov    %rbx,0x38(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:542
  15d689:	48 8b 44 24 18       	mov    0x18(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  15d68e:	48 89 44 24 48       	mov    %rax,0x48(%rsp)
  15d693:	eb 0c                	jmp    15d6a1 <AbstractOdometer::CalPose()+0x211>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  15d695:	66 0f 10 02          	movupd (%rdx),%xmm0
  15d699:	66 41 0f 11 07       	movupd %xmm0,(%r15)
  15d69e:	4c 89 fb             	mov    %r15,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  15d6a1:	4c 8b 6c 24 10       	mov    0x10(%rsp),%r13
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  15d6a6:	4c 89 6c 24 40       	mov    %r13,0x40(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  15d6ab:	48 89 54 24 08       	mov    %rdx,0x8(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  15d6b0:	48 c7 44 24 10 00 00 	movq   $0x0,0x10(%rsp)
  15d6b7:	00 00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  15d6b9:	c6 44 24 18 00       	movb   $0x0,0x18(%rsp)
std::_Function_base::_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:271
  15d6be:	48 c7 84 24 90 00 00 	movq   $0x0,0x90(%rsp)
  15d6c5:	00 00 00 00 00 
std::_Function_base::_Base_manager<std::_Bind<AbstractOdometer::CalPose()::$_11 ()> >::_M_init_functor(std::_Any_data&, std::_Bind<AbstractOdometer::CalPose()::$_11 ()>&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  15d6ca:	bf 28 00 00 00       	mov    $0x28,%edi
  15d6cf:	e8 ec 5f f2 ff       	call   836c0 <operator new(unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:182
  15d6d4:	48 89 c1             	mov    %rax,%rcx
  15d6d7:	48 83 c1 10          	add    $0x10,%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  15d6db:	48 89 08             	mov    %rcx,(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  15d6de:	4c 39 fb             	cmp    %r15,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:534
  15d6e1:	74 0e                	je     15d6f1 <AbstractOdometer::CalPose()+0x261>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  15d6e3:	48 89 18             	mov    %rbx,(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:542
  15d6e6:	48 8b 4c 24 48       	mov    0x48(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  15d6eb:	48 89 48 10          	mov    %rcx,0x10(%rax)
  15d6ef:	eb 09                	jmp    15d6fa <AbstractOdometer::CalPose()+0x26a>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  15d6f1:	66 41 0f 10 07       	movupd (%r15),%xmm0
  15d6f6:	66 0f 11 01          	movupd %xmm0,(%rcx)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  15d6fa:	4c 89 7c 24 38       	mov    %r15,0x38(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  15d6ff:	48 c7 44 24 40 00 00 	movq   $0x0,0x40(%rsp)
  15d706:	00 00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  15d708:	c6 44 24 48 00       	movb   $0x0,0x48(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  15d70d:	4c 89 68 08          	mov    %r13,0x8(%rax)
std::_Function_base::_Base_manager<std::_Bind<AbstractOdometer::CalPose()::$_11 ()> >::_M_init_functor(std::_Any_data&, std::_Bind<AbstractOdometer::CalPose()::$_11 ()>&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  15d711:	48 89 84 24 80 00 00 	mov    %rax,0x80(%rsp)
  15d718:	00 
std::function<void ()>::function<std::_Bind<AbstractOdometer::CalPose()::$_11 ()>, void, void>(std::_Bind<AbstractOdometer::CalPose()::$_11 ()>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:694
  15d719:	48 8d 05 60 4c 00 00 	lea    0x4c60(%rip),%rax        # 162380 <std::_Function_handler<void (), std::_Bind<AbstractOdometer::CalPose()::$_11 ()> >::_M_invoke(std::_Any_data const&)>
  15d720:	48 89 84 24 98 00 00 	mov    %rax,0x98(%rsp)
  15d727:	00 
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:695
  15d728:	48 8d 05 31 4e 00 00 	lea    0x4e31(%rip),%rax        # 162560 <std::_Function_base::_Base_manager<std::_Bind<AbstractOdometer::CalPose()::$_11 ()> >::_M_manager(std::_Any_data&, std::_Any_data const&, std::_Manager_operation)>
  15d72f:	48 89 84 24 90 00 00 	mov    %rax,0x90(%rsp)
  15d736:	00 
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1294
  15d737:	48 c7 44 24 28 00 00 	movq   $0x0,0x28(%rsp)
  15d73e:	00 00 
  15d740:	48 8d 7c 24 30       	lea    0x30(%rsp),%rdi
AbstractOdometer::CalPose():
  15d745:	48 8d 54 24 60       	lea    0x60(%rsp),%rdx
  15d74a:	48 8d 8c 24 80 00 00 	lea    0x80(%rsp),%rcx
  15d751:	00 
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1294
  15d752:	31 f6                	xor    %esi,%esi
  15d754:	e8 e7 93 f2 ff       	call   86b40 <std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count<std::packaged_task<void ()>, std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::packaged_task<void ()>*, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&)@plt>
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_get_deleter(std::type_info const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:727
  15d759:	48 8b 7c 24 30       	mov    0x30(%rsp),%rdi
  15d75e:	48 85 ff             	test   %rdi,%rdi
  15d761:	74 17                	je     15d77a <AbstractOdometer::CalPose()+0x2ea>
  15d763:	48 8b 07             	mov    (%rdi),%rax
  15d766:	48 8b 35 e3 a0 2a 00 	mov    0x2aa0e3(%rip),%rsi        # 407850 <typeinfo for std::_Sp_make_shared_tag@@Base+0x6d08>
  15d76d:	ff 50 20             	call   *0x20(%rax)
  15d770:	48 89 c3             	mov    %rax,%rbx
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:688
  15d773:	4c 8b 7c 24 30       	mov    0x30(%rsp),%r15
  15d778:	eb 05                	jmp    15d77f <AbstractOdometer::CalPose()+0x2ef>
AbstractOdometer::CalPose():
  15d77a:	45 31 ff             	xor    %r15d,%r15d
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_get_deleter(std::type_info const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:727
  15d77d:	31 db                	xor    %ebx,%ebx
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1300
  15d77f:	48 89 5c 24 28       	mov    %rbx,0x28(%rsp)
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:690
  15d784:	4d 85 ff             	test   %r15,%r15
  15d787:	74 17                	je     15d7a0 <AbstractOdometer::CalPose()+0x310>
__gnu_cxx::__atomic_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:95
  15d789:	48 83 3d 17 a3 2a 00 	cmpq   $0x0,0x2aa317(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  15d790:	00 
  15d791:	74 08                	je     15d79b <AbstractOdometer::CalPose()+0x30b>
__gnu_cxx::__atomic_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:53
  15d793:	f0 41 83 47 08 01    	lock addl $0x1,0x8(%r15)
  15d799:	eb 05                	jmp    15d7a0 <AbstractOdometer::CalPose()+0x310>
__gnu_cxx::__atomic_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:74
  15d79b:	41 83 47 08 01       	addl   $0x1,0x8(%r15)
std::_Function_base::_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:271
  15d7a0:	48 c7 44 24 70 00 00 	movq   $0x0,0x70(%rsp)
  15d7a7:	00 00 
std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<AbstractOdometer::CalPose()::$_11>(AbstractOdometer::CalPose()::$_11&&)::{lambda()#1}>::_M_init_functor(std::_Any_data&, rbk::Logger::Thread::move2thread<AbstractOdometer::CalPose()::$_11>(AbstractOdometer::CalPose()::$_11&&)::{lambda()#1}&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  15d7a9:	bf 10 00 00 00       	mov    $0x10,%edi
  15d7ae:	e8 0d 5f f2 ff       	call   836c0 <operator new(unsigned long)@plt>
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr(std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1131
  15d7b3:	48 89 18             	mov    %rbx,(%rax)
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_swap(std::__shared_count<(__gnu_cxx::_Lock_policy)2>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:714
  15d7b6:	4c 89 78 08          	mov    %r15,0x8(%rax)
std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<AbstractOdometer::CalPose()::$_11>(AbstractOdometer::CalPose()::$_11&&)::{lambda()#1}>::_M_init_functor(std::_Any_data&, rbk::Logger::Thread::move2thread<AbstractOdometer::CalPose()::$_11>(AbstractOdometer::CalPose()::$_11&&)::{lambda()#1}&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  15d7ba:	48 89 44 24 60       	mov    %rax,0x60(%rsp)
std::function<void ()>::function<rbk::Logger::Thread::move2thread<AbstractOdometer::CalPose()::$_11>(AbstractOdometer::CalPose()::$_11&&)::{lambda()#1}, void, void>(rbk::Logger::Thread::move2thread<AbstractOdometer::CalPose()::$_11>(AbstractOdometer::CalPose()::$_11&&)::{lambda()#1}):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:694
  15d7bf:	48 8d 05 ca 4e 00 00 	lea    0x4eca(%rip),%rax        # 162690 <std::_Function_handler<void (), rbk::Logger::Thread::move2thread<AbstractOdometer::CalPose()::$_11>(AbstractOdometer::CalPose()::$_11&&)::{lambda()#1}>::_M_invoke(std::_Any_data const&)>
  15d7c6:	48 89 44 24 78       	mov    %rax,0x78(%rsp)
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:695
  15d7cb:	48 8d 05 ee 4e 00 00 	lea    0x4eee(%rip),%rax        # 1626c0 <std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<AbstractOdometer::CalPose()::$_11>(AbstractOdometer::CalPose()::$_11&&)::{lambda()#1}>::_M_manager(std::_Any_data&, std::_Any_data const&, std::_Manager_operation)>
  15d7d2:	48 89 44 24 70       	mov    %rax,0x70(%rsp)
std::future<decltype ({parm#1}({parm#2}...))> rbk::Logger::Thread::move2thread<AbstractOdometer::CalPose()::$_11>(AbstractOdometer::CalPose()::$_11&&):
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:204
  15d7d7:	49 8d 7e 08          	lea    0x8(%r14),%rdi
  15d7db:	48 8d 74 24 60       	lea    0x60(%rsp),%rsi
  15d7e0:	e8 cb 65 f2 ff       	call   83db0 <rbk::Logger::Thread::SafeQueue<std::function<void ()> >::push_back(std::function<void ()>&)@plt>
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:206
  15d7e5:	49 81 c6 c0 01 00 00 	add    $0x1c0,%r14
  15d7ec:	4c 89 f7             	mov    %r14,%rdi
  15d7ef:	e8 bc 74 f2 ff       	call   84cb0 <std::condition_variable::notify_one()@plt>
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::get() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1258
  15d7f4:	48 8b 74 24 28       	mov    0x28(%rsp),%rsi
  15d7f9:	48 8d bc 24 f0 00 00 	lea    0xf0(%rsp),%rdi
  15d800:	00 
std::future<decltype ({parm#1}({parm#2}...))> rbk::Logger::Thread::move2thread<AbstractOdometer::CalPose()::$_11>(AbstractOdometer::CalPose()::$_11&&):
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:207
  15d801:	e8 4a 87 f2 ff       	call   85f50 <std::packaged_task<void ()>::get_future()@plt>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  15d806:	48 8b 44 24 70       	mov    0x70(%rsp),%rax
  15d80b:	48 85 c0             	test   %rax,%rax
  15d80e:	74 0f                	je     15d81f <AbstractOdometer::CalPose()+0x38f>
AbstractOdometer::CalPose():
  15d810:	48 8d 7c 24 60       	lea    0x60(%rsp),%rdi
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  15d815:	ba 03 00 00 00       	mov    $0x3,%edx
  15d81a:	48 89 fe             	mov    %rdi,%rsi
  15d81d:	ff d0                	call   *%rax
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  15d81f:	4c 8b 74 24 30       	mov    0x30(%rsp),%r14
  15d824:	4d 85 f6             	test   %r14,%r14
  15d827:	74 6a                	je     15d893 <AbstractOdometer::CalPose()+0x403>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  15d829:	48 83 3d 77 a2 2a 00 	cmpq   $0x0,0x2aa277(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  15d830:	00 
  15d831:	74 12                	je     15d845 <AbstractOdometer::CalPose()+0x3b5>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  15d833:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  15d838:	f0 41 0f c1 46 08    	lock xadd %eax,0x8(%r14)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  15d83e:	83 f8 01             	cmp    $0x1,%eax
  15d841:	74 12                	je     15d855 <AbstractOdometer::CalPose()+0x3c5>
  15d843:	eb 4e                	jmp    15d893 <AbstractOdometer::CalPose()+0x403>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  15d845:	41 8b 46 08          	mov    0x8(%r14),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  15d849:	8d 48 ff             	lea    -0x1(%rax),%ecx
  15d84c:	41 89 4e 08          	mov    %ecx,0x8(%r14)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  15d850:	83 f8 01             	cmp    $0x1,%eax
  15d853:	75 3e                	jne    15d893 <AbstractOdometer::CalPose()+0x403>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  15d855:	49 8b 06             	mov    (%r14),%rax
  15d858:	4c 89 f7             	mov    %r14,%rdi
  15d85b:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  15d85e:	48 83 3d 42 a2 2a 00 	cmpq   $0x0,0x2aa242(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  15d865:	00 
  15d866:	74 12                	je     15d87a <AbstractOdometer::CalPose()+0x3ea>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  15d868:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  15d86d:	f0 41 0f c1 46 0c    	lock xadd %eax,0xc(%r14)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  15d873:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  15d876:	74 12                	je     15d88a <AbstractOdometer::CalPose()+0x3fa>
  15d878:	eb 19                	jmp    15d893 <AbstractOdometer::CalPose()+0x403>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  15d87a:	41 8b 46 0c          	mov    0xc(%r14),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  15d87e:	8d 48 ff             	lea    -0x1(%rax),%ecx
  15d881:	41 89 4e 0c          	mov    %ecx,0xc(%r14)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  15d885:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  15d888:	75 09                	jne    15d893 <AbstractOdometer::CalPose()+0x403>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  15d88a:	49 8b 06             	mov    (%r14),%rax
  15d88d:	4c 89 f7             	mov    %r14,%rdi
  15d890:	ff 50 18             	call   *0x18(%rax)
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  15d893:	48 8b 84 24 90 00 00 	mov    0x90(%rsp),%rax
  15d89a:	00 
  15d89b:	48 85 c0             	test   %rax,%rax
  15d89e:	74 12                	je     15d8b2 <AbstractOdometer::CalPose()+0x422>
AbstractOdometer::CalPose():
  15d8a0:	48 8d bc 24 80 00 00 	lea    0x80(%rsp),%rdi
  15d8a7:	00 
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  15d8a8:	ba 03 00 00 00       	mov    $0x3,%edx
  15d8ad:	48 89 fe             	mov    %rdi,%rsi
  15d8b0:	ff d0                	call   *%rax
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  15d8b2:	4c 8b b4 24 f8 00 00 	mov    0xf8(%rsp),%r14
  15d8b9:	00 
  15d8ba:	4d 85 f6             	test   %r14,%r14
  15d8bd:	74 6a                	je     15d929 <AbstractOdometer::CalPose()+0x499>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  15d8bf:	48 83 3d e1 a1 2a 00 	cmpq   $0x0,0x2aa1e1(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  15d8c6:	00 
  15d8c7:	74 12                	je     15d8db <AbstractOdometer::CalPose()+0x44b>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  15d8c9:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  15d8ce:	f0 41 0f c1 46 08    	lock xadd %eax,0x8(%r14)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  15d8d4:	83 f8 01             	cmp    $0x1,%eax
  15d8d7:	74 12                	je     15d8eb <AbstractOdometer::CalPose()+0x45b>
  15d8d9:	eb 4e                	jmp    15d929 <AbstractOdometer::CalPose()+0x499>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  15d8db:	41 8b 46 08          	mov    0x8(%r14),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  15d8df:	8d 48 ff             	lea    -0x1(%rax),%ecx
  15d8e2:	41 89 4e 08          	mov    %ecx,0x8(%r14)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  15d8e6:	83 f8 01             	cmp    $0x1,%eax
  15d8e9:	75 3e                	jne    15d929 <AbstractOdometer::CalPose()+0x499>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  15d8eb:	49 8b 06             	mov    (%r14),%rax
  15d8ee:	4c 89 f7             	mov    %r14,%rdi
  15d8f1:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  15d8f4:	48 83 3d ac a1 2a 00 	cmpq   $0x0,0x2aa1ac(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  15d8fb:	00 
  15d8fc:	74 12                	je     15d910 <AbstractOdometer::CalPose()+0x480>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  15d8fe:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  15d903:	f0 41 0f c1 46 0c    	lock xadd %eax,0xc(%r14)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  15d909:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  15d90c:	74 12                	je     15d920 <AbstractOdometer::CalPose()+0x490>
  15d90e:	eb 19                	jmp    15d929 <AbstractOdometer::CalPose()+0x499>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  15d910:	41 8b 46 0c          	mov    0xc(%r14),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  15d914:	8d 48 ff             	lea    -0x1(%rax),%ecx
  15d917:	41 89 4e 0c          	mov    %ecx,0xc(%r14)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  15d91b:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  15d91e:	75 09                	jne    15d929 <AbstractOdometer::CalPose()+0x499>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  15d920:	49 8b 06             	mov    (%r14),%rax
  15d923:	4c 89 f7             	mov    %r14,%rdi
  15d926:	ff 50 18             	call   *0x18(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  15d929:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  15d92e:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  15d933:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  15d936:	74 05                	je     15d93d <AbstractOdometer::CalPose()+0x4ad>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  15d938:	e8 f3 70 f2 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  15d93d:	48 8b bc 24 b0 00 00 	mov    0xb0(%rsp),%rdi
  15d944:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  15d945:	48 8d 84 24 c0 00 00 	lea    0xc0(%rsp),%rax
  15d94c:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  15d94d:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  15d950:	74 05                	je     15d957 <AbstractOdometer::CalPose()+0x4c7>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  15d952:	e8 d9 70 f2 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::~basic_stringstream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:731
  15d957:	48 8b 1d 0a a1 2a 00 	mov    0x2aa10a(%rip),%rbx        # 407a68 <VTT for std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  15d95e:	48 8b 03             	mov    (%rbx),%rax
  15d961:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  15d968:	00 
  15d969:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  15d96d:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  15d971:	48 89 8c 04 00 01 00 	mov    %rcx,0x100(%rsp,%rax,1)
  15d978:	00 
  15d979:	48 8b 43 48          	mov    0x48(%rbx),%rax
  15d97d:	48 89 84 24 10 01 00 	mov    %rax,0x110(%rsp)
  15d984:	00 
std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::~basic_stringbuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/sstream.tcc:291
  15d985:	48 8b 05 dc 94 2a 00 	mov    0x2a94dc(%rip),%rax        # 406e68 <vtable for std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  15d98c:	48 83 c0 10          	add    $0x10,%rax
  15d990:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  15d997:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  15d998:	48 8b bc 24 60 01 00 	mov    0x160(%rsp),%rdi
  15d99f:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  15d9a0:	48 8d 84 24 70 01 00 	lea    0x170(%rsp),%rax
  15d9a7:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  15d9a8:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  15d9ab:	74 05                	je     15d9b2 <AbstractOdometer::CalPose()+0x522>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  15d9ad:	e8 7e 70 f2 ff       	call   84a30 <operator delete(void*)@plt>
std::basic_streambuf<char, std::char_traits<char> >::~basic_streambuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/streambuf:198
  15d9b2:	48 8b 05 5f 9f 2a 00 	mov    0x2a9f5f(%rip),%rax        # 407918 <vtable for std::basic_streambuf<char, std::char_traits<char> >@GLIBCXX_3.4>
  15d9b9:	48 83 c0 10          	add    $0x10,%rax
  15d9bd:	48 89 84 24 18 01 00 	mov    %rax,0x118(%rsp)
  15d9c4:	00 
  15d9c5:	48 8d bc 24 50 01 00 	lea    0x150(%rsp),%rdi
  15d9cc:	00 
  15d9cd:	e8 5e 88 f2 ff       	call   86230 <std::locale::~locale()@plt>
std::basic_istream<char, std::char_traits<char> >::~basic_istream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/istream:104
  15d9d2:	48 8b 43 10          	mov    0x10(%rbx),%rax
  15d9d6:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  15d9da:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  15d9e1:	00 
  15d9e2:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  15d9e6:	48 89 8c 04 00 01 00 	mov    %rcx,0x100(%rsp,%rax,1)
  15d9ed:	00 
  15d9ee:	48 c7 84 24 08 01 00 	movq   $0x0,0x108(%rsp)
  15d9f5:	00 00 00 00 00 
std::basic_ios<char, std::char_traits<char> >::~basic_ios():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:282
  15d9fa:	48 8d bc 24 80 01 00 	lea    0x180(%rsp),%rdi
  15da01:	00 
  15da02:	e8 19 79 f2 ff       	call   85320 <std::ios_base::~ios_base()@plt>
  15da07:	66 0f 28 84 24 a0 00 	movapd 0xa0(%rsp),%xmm0
  15da0e:	00 00 
AbstractOdometer::CalPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:446
  15da10:	f2 41 0f 58 84 24 18 	addsd  0x118(%r12),%xmm0
  15da17:	01 00 00 
  15da1a:	f2 41 0f 11 84 24 18 	movsd  %xmm0,0x118(%r12)
  15da21:	01 00 00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:447
  15da24:	e8 37 79 f2 ff       	call   85360 <rbk::foundation::utils::Normalize(double)@plt>
  15da29:	f2 41 0f 11 84 24 18 	movsd  %xmm0,0x118(%r12)
  15da30:	01 00 00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:448
  15da33:	e8 c8 66 f2 ff       	call   84100 <sin@plt>
  15da38:	66 0f 29 84 24 a0 00 	movapd %xmm0,0xa0(%rsp)
  15da3f:	00 00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:449
  15da41:	f2 41 0f 10 84 24 18 	movsd  0x118(%r12),%xmm0
  15da48:	01 00 00 
  15da4b:	e8 d0 84 f2 ff       	call   85f20 <cos@plt>
  15da50:	66 0f 28 94 24 d0 00 	movapd 0xd0(%rsp),%xmm2
  15da57:	00 00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:450
  15da59:	66 0f 14 d2          	unpcklpd %xmm2,%xmm2
  15da5d:	66 0f 28 c8          	movapd %xmm0,%xmm1
  15da61:	66 0f 28 9c 24 a0 00 	movapd 0xa0(%rsp),%xmm3
  15da68:	00 00 
  15da6a:	66 0f 14 cb          	unpcklpd %xmm3,%xmm1
  15da6e:	66 0f 59 ca          	mulpd  %xmm2,%xmm1
  15da72:	66 0f 28 94 24 e0 00 	movapd 0xe0(%rsp),%xmm2
  15da79:	00 00 
  15da7b:	66 0f 14 d2          	unpcklpd %xmm2,%xmm2
  15da7f:	66 0f 14 d8          	unpcklpd %xmm0,%xmm3
  15da83:	66 0f 59 da          	mulpd  %xmm2,%xmm3
  15da87:	66 0f 28 c1          	movapd %xmm1,%xmm0
  15da8b:	66 0f 5c c3          	subpd  %xmm3,%xmm0
  15da8f:	66 0f 58 d9          	addpd  %xmm1,%xmm3
  15da93:	f2 0f 10 d8          	movsd  %xmm0,%xmm3
  15da97:	66 41 0f 10 84 24 08 	movupd 0x108(%r12),%xmm0
  15da9e:	01 00 00 
  15daa1:	66 0f 58 c3          	addpd  %xmm3,%xmm0
  15daa5:	66 41 0f 11 84 24 08 	movupd %xmm0,0x108(%r12)
  15daac:	01 00 00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/odometer.cpp:454
  15daaf:	b0 01                	mov    $0x1,%al
  15dab1:	48 8d 65 d8          	lea    -0x28(%rbp),%rsp
  15dab5:	5b                   	pop    %rbx
  15dab6:	41 5c                	pop    %r12
  15dab8:	41 5d                	pop    %r13
  15daba:	41 5e                	pop    %r14
  15dabc:	41 5f                	pop    %r15
  15dabe:	5d                   	pop    %rbp
  15dabf:	c3                   	ret    
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:212
  15dac0:	48 8d 3d ee ff 02 00 	lea    0x2ffee(%rip),%rdi        # 18dab5 <typeinfo name for rbk::Logger::Thread::move2thread<OdoCalculator::run()::$_32>(OdoCalculator::run()::$_32&&)::{lambda()#1}+0x1755>
  15dac7:	e8 64 58 f2 ff       	call   83330 <std::__throw_logic_error(char const*)@plt>
AbstractOdometer::CalPose():
  15dacc:	e9 b0 00 00 00       	jmp    15db81 <AbstractOdometer::CalPose()+0x6f1>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  15dad1:	48 89 c7             	mov    %rax,%rdi
  15dad4:	e8 c7 92 f4 ff       	call   a6da0 <__clang_call_terminate>
  15dad9:	48 89 c7             	mov    %rax,%rdi
  15dadc:	e8 bf 92 f4 ff       	call   a6da0 <__clang_call_terminate>
AbstractOdometer::CalPose():
  15dae1:	49 89 c6             	mov    %rax,%r14
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:690
  15dae4:	4d 85 ff             	test   %r15,%r15
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  15dae7:	0f 84 c8 00 00 00    	je     15dbb5 <AbstractOdometer::CalPose()+0x725>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  15daed:	48 83 3d b3 9f 2a 00 	cmpq   $0x0,0x2a9fb3(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  15daf4:	00 
  15daf5:	74 15                	je     15db0c <AbstractOdometer::CalPose()+0x67c>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  15daf7:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  15dafc:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  15db02:	83 f8 01             	cmp    $0x1,%eax
  15db05:	74 19                	je     15db20 <AbstractOdometer::CalPose()+0x690>
  15db07:	e9 a9 00 00 00       	jmp    15dbb5 <AbstractOdometer::CalPose()+0x725>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  15db0c:	41 8b 47 08          	mov    0x8(%r15),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  15db10:	8d 48 ff             	lea    -0x1(%rax),%ecx
  15db13:	41 89 4f 08          	mov    %ecx,0x8(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  15db17:	83 f8 01             	cmp    $0x1,%eax
  15db1a:	0f 85 95 00 00 00    	jne    15dbb5 <AbstractOdometer::CalPose()+0x725>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  15db20:	49 8b 07             	mov    (%r15),%rax
  15db23:	4c 89 ff             	mov    %r15,%rdi
  15db26:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  15db29:	48 83 3d 77 9f 2a 00 	cmpq   $0x0,0x2a9f77(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  15db30:	00 
  15db31:	74 12                	je     15db45 <AbstractOdometer::CalPose()+0x6b5>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  15db33:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  15db38:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  15db3e:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  15db41:	74 12                	je     15db55 <AbstractOdometer::CalPose()+0x6c5>
  15db43:	eb 70                	jmp    15dbb5 <AbstractOdometer::CalPose()+0x725>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  15db45:	41 8b 47 0c          	mov    0xc(%r15),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  15db49:	8d 48 ff             	lea    -0x1(%rax),%ecx
  15db4c:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  15db50:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  15db53:	75 60                	jne    15dbb5 <AbstractOdometer::CalPose()+0x725>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  15db55:	49 8b 07             	mov    (%r15),%rax
  15db58:	4c 89 ff             	mov    %r15,%rdi
  15db5b:	ff 50 18             	call   *0x18(%rax)
  15db5e:	eb 55                	jmp    15dbb5 <AbstractOdometer::CalPose()+0x725>
AbstractOdometer::CalPose():
  15db60:	49 89 c6             	mov    %rax,%r14
  15db63:	e9 bb 00 00 00       	jmp    15dc23 <AbstractOdometer::CalPose()+0x793>
  15db68:	49 89 c6             	mov    %rax,%r14
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  15db6b:	4c 39 fb             	cmp    %r15,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  15db6e:	0f 84 ce 00 00 00    	je     15dc42 <AbstractOdometer::CalPose()+0x7b2>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  15db74:	48 89 df             	mov    %rbx,%rdi
  15db77:	e8 b4 6e f2 ff       	call   84a30 <operator delete(void*)@plt>
  15db7c:	e9 c1 00 00 00       	jmp    15dc42 <AbstractOdometer::CalPose()+0x7b2>
AbstractOdometer::CalPose():
  15db81:	49 89 c6             	mov    %rax,%r14
  15db84:	e9 cd 00 00 00       	jmp    15dc56 <AbstractOdometer::CalPose()+0x7c6>
  15db89:	49 89 c6             	mov    %rax,%r14
  15db8c:	e9 df 00 00 00       	jmp    15dc70 <AbstractOdometer::CalPose()+0x7e0>
  15db91:	49 89 c6             	mov    %rax,%r14
  15db94:	e9 d7 00 00 00       	jmp    15dc70 <AbstractOdometer::CalPose()+0x7e0>
  15db99:	49 89 c6             	mov    %rax,%r14
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  15db9c:	48 8b 4c 24 70       	mov    0x70(%rsp),%rcx
  15dba1:	48 85 c9             	test   %rcx,%rcx
  15dba4:	74 0f                	je     15dbb5 <AbstractOdometer::CalPose()+0x725>
AbstractOdometer::CalPose():
  15dba6:	48 8d 7c 24 60       	lea    0x60(%rsp),%rdi
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  15dbab:	ba 03 00 00 00       	mov    $0x3,%edx
  15dbb0:	48 89 fe             	mov    %rdi,%rsi
  15dbb3:	ff d1                	call   *%rcx
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  15dbb5:	48 8b 5c 24 30       	mov    0x30(%rsp),%rbx
  15dbba:	48 85 db             	test   %rbx,%rbx
  15dbbd:	74 64                	je     15dc23 <AbstractOdometer::CalPose()+0x793>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  15dbbf:	48 83 3d e1 9e 2a 00 	cmpq   $0x0,0x2a9ee1(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  15dbc6:	00 
  15dbc7:	74 11                	je     15dbda <AbstractOdometer::CalPose()+0x74a>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  15dbc9:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  15dbce:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  15dbd3:	83 f8 01             	cmp    $0x1,%eax
  15dbd6:	74 10                	je     15dbe8 <AbstractOdometer::CalPose()+0x758>
  15dbd8:	eb 49                	jmp    15dc23 <AbstractOdometer::CalPose()+0x793>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  15dbda:	8b 43 08             	mov    0x8(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  15dbdd:	8d 48 ff             	lea    -0x1(%rax),%ecx
  15dbe0:	89 4b 08             	mov    %ecx,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  15dbe3:	83 f8 01             	cmp    $0x1,%eax
  15dbe6:	75 3b                	jne    15dc23 <AbstractOdometer::CalPose()+0x793>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  15dbe8:	48 8b 03             	mov    (%rbx),%rax
  15dbeb:	48 89 df             	mov    %rbx,%rdi
  15dbee:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  15dbf1:	48 83 3d af 9e 2a 00 	cmpq   $0x0,0x2a9eaf(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  15dbf8:	00 
  15dbf9:	74 11                	je     15dc0c <AbstractOdometer::CalPose()+0x77c>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  15dbfb:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
