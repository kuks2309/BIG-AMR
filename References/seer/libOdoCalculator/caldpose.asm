
/media/amap/6ab6980d-f090-4387-8753-a2251e75651d/usr/local/SeerRobotics/rbk/plugins/libOdoCalculator.so:     file format elf64-x86-64


Disassembly of section .text:

000000000014f300 <MultiSteersOdometer::CaldPose()>:
MultiSteersOdometer::CaldPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:159
  14f300:	55                   	push   %rbp
  14f301:	48 89 e5             	mov    %rsp,%rbp
  14f304:	41 57                	push   %r15
  14f306:	41 56                	push   %r14
  14f308:	41 55                	push   %r13
  14f30a:	41 54                	push   %r12
  14f30c:	53                   	push   %rbx
  14f30d:	48 83 e4 f0          	and    $0xfffffffffffffff0,%rsp
  14f311:	48 81 ec c0 02 00 00 	sub    $0x2c0,%rsp
  14f318:	48 89 fb             	mov    %rdi,%rbx
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:160
  14f31b:	e8 30 59 f3 ff       	call   84c50 <AbstractOdometer::CaldPose()@plt>
  14f320:	84 c0                	test   %al,%al
  14f322:	0f 84 53 04 00 00    	je     14f77b <MultiSteersOdometer::CaldPose()+0x47b>
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:163
  14f328:	80 7b 0b 00          	cmpb   $0x0,0xb(%rbx)
  14f32c:	0f 84 50 04 00 00    	je     14f782 <MultiSteersOdometer::CaldPose()+0x482>
std::_Rb_tree<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::_Select1st<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > >::size() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:997
  14f332:	4c 8b bb 70 01 00 00 	mov    0x170(%rbx),%r15
MultiSteersOdometer::CaldPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:166
  14f339:	4d 01 ff             	add    %r15,%r15
Eigen::DenseStorage<double, -1, -1, 1, 0>::DenseStorage():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:500
  14f33c:	66 0f 57 c0          	xorpd  %xmm0,%xmm0
  14f340:	66 0f 29 44 24 30    	movapd %xmm0,0x30(%rsp)
MultiSteersOdometer::CaldPose():
  14f346:	48 8d 7c 24 30       	lea    0x30(%rsp),%rdi
void Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> >::resizeLike<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >(Eigen::EigenBase<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > > const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/PlainObjectBase.h:375
  14f34b:	ba 01 00 00 00       	mov    $0x1,%edx
  14f350:	4c 89 fe             	mov    %r15,%rsi
  14f353:	e8 08 58 f3 ff       	call   84b60 <Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> >::resize(long, long)@plt>
void Eigen::internal::resize_if_allowed<Eigen::Matrix<double, -1, 1, 0, -1, 1>, Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> >, double, double>(Eigen::Matrix<double, -1, 1, 0, -1, 1>&, Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > const&, Eigen::internal::assign_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:719
  14f358:	4c 39 7c 24 38       	cmp    %r15,0x38(%rsp)
  14f35d:	48 89 5c 24 40       	mov    %rbx,0x40(%rsp)
  14f362:	74 17                	je     14f37b <MultiSteersOdometer::CaldPose()+0x7b>
MultiSteersOdometer::CaldPose():
  14f364:	48 8d 7c 24 30       	lea    0x30(%rsp),%rdi
void Eigen::internal::resize_if_allowed<Eigen::Matrix<double, -1, 1, 0, -1, 1>, Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> >, double, double>(Eigen::Matrix<double, -1, 1, 0, -1, 1>&, Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > const&, Eigen::internal::assign_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:720
  14f369:	ba 01 00 00 00       	mov    $0x1,%edx
  14f36e:	4c 89 fe             	mov    %r15,%rsi
  14f371:	e8 ea 57 f3 ff       	call   84b60 <Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> >::resize(long, long)@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::rows() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:544
  14f376:	4c 8b 7c 24 38       	mov    0x38(%rsp),%r15
Eigen::DenseStorage<double, -1, -1, 1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:564
  14f37b:	4c 8b 74 24 30       	mov    0x30(%rsp),%r14
Eigen::internal::dense_assignment_loop<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >, Eigen::internal::assign_op<double, double>, 0>, 3, 0>::run(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >, Eigen::internal::assign_op<double, double>, 0>&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:411
  14f380:	4c 89 fb             	mov    %r15,%rbx
  14f383:	48 c1 eb 3f          	shr    $0x3f,%rbx
  14f387:	4c 01 fb             	add    %r15,%rbx
  14f38a:	49 89 dc             	mov    %rbx,%r12
  14f38d:	49 83 e4 fe          	and    $0xfffffffffffffffe,%r12
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14f391:	49 83 ff 02          	cmp    $0x2,%r15
  14f395:	7c 27                	jl     14f3be <MultiSteersOdometer::CaldPose()+0xbe>
  14f397:	49 83 fc 01          	cmp    $0x1,%r12
  14f39b:	b8 02 00 00 00       	mov    $0x2,%eax
  14f3a0:	49 0f 4f c4          	cmovg  %r12,%rax
  14f3a4:	48 8d 14 c5 f8 ff ff 	lea    -0x8(,%rax,8),%rdx
  14f3ab:	ff 
  14f3ac:	48 83 e2 f0          	and    $0xfffffffffffffff0,%rdx
  14f3b0:	48 83 c2 10          	add    $0x10,%rdx
void Eigen::internal::pstore<double, double __vector(2)>(double*, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:359
  14f3b4:	31 f6                	xor    %esi,%esi
  14f3b6:	4c 89 f7             	mov    %r14,%rdi
  14f3b9:	e8 c2 4a f3 ff       	call   83e80 <memset@plt>
MultiSteersOdometer::CaldPose():
  14f3be:	48 8b 44 24 40       	mov    0x40(%rsp),%rax
  14f3c3:	4c 8d a8 48 01 00 00 	lea    0x148(%rax),%r13
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >, Eigen::internal::assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >, Eigen::internal::assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14f3ca:	4d 39 fc             	cmp    %r15,%r12
  14f3cd:	7d 1c                	jge    14f3eb <MultiSteersOdometer::CaldPose()+0xeb>
MultiSteersOdometer::CaldPose():
  14f3cf:	48 d1 fb             	sar    %rbx
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >, Eigen::internal::assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >, Eigen::internal::assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14f3d2:	4b 8d 3c e6          	lea    (%r14,%r12,8),%rdi
  14f3d6:	49 c1 e7 03          	shl    $0x3,%r15
  14f3da:	48 c1 e3 04          	shl    $0x4,%rbx
  14f3de:	49 29 df             	sub    %rbx,%r15
Eigen::internal::assign_op<double, double>::assignCoeff(double&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/AssignmentFunctors.h:24
  14f3e1:	31 f6                	xor    %esi,%esi
  14f3e3:	4c 89 fa             	mov    %r15,%rdx
  14f3e6:	e8 95 4a f3 ff       	call   83e80 <memset@plt>
std::_Rb_tree<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::_Select1st<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > >::begin():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:961
  14f3eb:	4d 8b 7d 18          	mov    0x18(%r13),%r15
std::_Rb_tree<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::_Select1st<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > >::end():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:969
  14f3ef:	49 83 c5 08          	add    $0x8,%r13
  14f3f3:	4c 89 ac 24 c8 00 00 	mov    %r13,0xc8(%rsp)
  14f3fa:	00 
std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >::operator!=(std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:320
  14f3fb:	4d 39 ef             	cmp    %r13,%r15
MultiSteersOdometer::CaldPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:168
  14f3fe:	0f 84 13 02 00 00    	je     14f617 <MultiSteersOdometer::CaldPose()+0x317>
  14f404:	4c 8d a4 24 40 01 00 	lea    0x140(%rsp),%r12
  14f40b:	00 
  14f40c:	48 8b 44 24 40       	mov    0x40(%rsp),%rax
  14f411:	4c 8d 68 40          	lea    0x40(%rax),%r13
  14f415:	31 db                	xor    %ebx,%ebx
  14f417:	4c 89 ac 24 c0 00 00 	mov    %r13,0xc0(%rsp)
  14f41e:	00 
  14f41f:	90                   	nop
  14f420:	48 89 9c 24 d8 00 00 	mov    %rbx,0xd8(%rsp)
  14f427:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14f428:	4c 89 a4 24 30 01 00 	mov    %r12,0x130(%rsp)
  14f42f:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f430:	4d 8b 6f 20          	mov    0x20(%r15),%r13
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14f434:	4d 8b 77 28          	mov    0x28(%r15),%r14
bool __gnu_cxx::__is_null_pointer<char>(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/type_traits.h:153
  14f438:	4d 85 ed             	test   %r13,%r13
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:211
  14f43b:	75 09                	jne    14f446 <MultiSteersOdometer::CaldPose()+0x146>
  14f43d:	4d 85 f6             	test   %r14,%r14
  14f440:	0f 85 4c 07 00 00    	jne    14fb92 <MultiSteersOdometer::CaldPose()+0x892>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:215
  14f446:	4c 89 74 24 08       	mov    %r14,0x8(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f44b:	4c 89 e0             	mov    %r12,%rax
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:217
  14f44e:	49 83 fe 10          	cmp    $0x10,%r14
  14f452:	72 29                	jb     14f47d <MultiSteersOdometer::CaldPose()+0x17d>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:219
  14f454:	31 d2                	xor    %edx,%edx
  14f456:	48 8d bc 24 30 01 00 	lea    0x130(%rsp),%rdi
  14f45d:	00 
  14f45e:	48 8d 74 24 08       	lea    0x8(%rsp),%rsi
  14f463:	e8 c8 5c f3 ff       	call   85130 <std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_create(unsigned long&, unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14f468:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  14f46f:	00 
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:220
  14f470:	48 8b 4c 24 08       	mov    0x8(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14f475:	48 89 8c 24 40 01 00 	mov    %rcx,0x140(%rsp)
  14f47c:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  14f47d:	4d 85 f6             	test   %r14,%r14
  14f480:	74 2c                	je     14f4ae <MultiSteersOdometer::CaldPose()+0x1ae>
  14f482:	49 83 fe 01          	cmp    $0x1,%r14
  14f486:	75 18                	jne    14f4a0 <MultiSteersOdometer::CaldPose()+0x1a0>
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14f488:	41 0f b6 4d 00       	movzbl 0x0(%r13),%ecx
  14f48d:	88 08                	mov    %cl,(%rax)
  14f48f:	eb 1d                	jmp    14f4ae <MultiSteersOdometer::CaldPose()+0x1ae>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14f491:	66 66 66 66 66 66 2e 	data16 data16 data16 data16 data16 cs nopw 0x0(%rax,%rax,1)
  14f498:	0f 1f 84 00 00 00 00 
  14f49f:	00 
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14f4a0:	48 89 c7             	mov    %rax,%rdi
  14f4a3:	4c 89 ee             	mov    %r13,%rsi
  14f4a6:	4c 89 f2             	mov    %r14,%rdx
  14f4a9:	e8 c2 3f f3 ff       	call   83470 <memcpy@plt>
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:232
  14f4ae:	48 8b 44 24 08       	mov    0x8(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14f4b3:	48 89 84 24 38 01 00 	mov    %rax,0x138(%rsp)
  14f4ba:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f4bb:	48 8b 8c 24 30 01 00 	mov    0x130(%rsp),%rcx
  14f4c2:	00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14f4c3:	c6 04 01 00          	movb   $0x0,(%rcx,%rax,1)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14f4c7:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  14f4cc:	48 89 44 24 08       	mov    %rax,0x8(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f4d1:	4d 8b 6f 40          	mov    0x40(%r15),%r13
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14f4d5:	49 8b 5f 48          	mov    0x48(%r15),%rbx
bool __gnu_cxx::__is_null_pointer<char>(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/type_traits.h:153
  14f4d9:	4d 85 ed             	test   %r13,%r13
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:211
  14f4dc:	75 09                	jne    14f4e7 <MultiSteersOdometer::CaldPose()+0x1e7>
  14f4de:	48 85 db             	test   %rbx,%rbx
  14f4e1:	0f 85 9f 06 00 00    	jne    14fb86 <MultiSteersOdometer::CaldPose()+0x886>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:215
  14f4e7:	48 89 5c 24 78       	mov    %rbx,0x78(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f4ec:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:217
  14f4f1:	48 83 fb 10          	cmp    $0x10,%rbx
  14f4f5:	72 20                	jb     14f517 <MultiSteersOdometer::CaldPose()+0x217>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:219
  14f4f7:	31 d2                	xor    %edx,%edx
  14f4f9:	48 8d 7c 24 08       	lea    0x8(%rsp),%rdi
  14f4fe:	48 8d 74 24 78       	lea    0x78(%rsp),%rsi
  14f503:	e8 28 5c f3 ff       	call   85130 <std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_create(unsigned long&, unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14f508:	48 89 44 24 08       	mov    %rax,0x8(%rsp)
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:220
  14f50d:	48 8b 4c 24 78       	mov    0x78(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14f512:	48 89 4c 24 18       	mov    %rcx,0x18(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  14f517:	48 85 db             	test   %rbx,%rbx
  14f51a:	74 22                	je     14f53e <MultiSteersOdometer::CaldPose()+0x23e>
  14f51c:	48 83 fb 01          	cmp    $0x1,%rbx
  14f520:	75 0e                	jne    14f530 <MultiSteersOdometer::CaldPose()+0x230>
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14f522:	41 0f b6 4d 00       	movzbl 0x0(%r13),%ecx
  14f527:	88 08                	mov    %cl,(%rax)
  14f529:	eb 13                	jmp    14f53e <MultiSteersOdometer::CaldPose()+0x23e>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14f52b:	0f 1f 44 00 00       	nopl   0x0(%rax,%rax,1)
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14f530:	48 89 c7             	mov    %rax,%rdi
  14f533:	4c 89 ee             	mov    %r13,%rsi
  14f536:	48 89 da             	mov    %rbx,%rdx
  14f539:	e8 32 3f f3 ff       	call   83470 <memcpy@plt>
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:232
  14f53e:	48 8b 44 24 78       	mov    0x78(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14f543:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f548:	48 8b 4c 24 08       	mov    0x8(%rsp),%rcx
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14f54d:	c6 04 01 00          	movb   $0x0,(%rcx,%rax,1)
  14f551:	4c 8b ac 24 c0 00 00 	mov    0xc0(%rsp),%r13
  14f558:	00 
MultiSteersOdometer::CaldPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:171
  14f559:	4c 89 ef             	mov    %r13,%rdi
  14f55c:	48 8d b4 24 30 01 00 	lea    0x130(%rsp),%rsi
  14f563:	00 
  14f564:	e8 b7 44 f3 ff       	call   83a20 <std::map<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, MotorVitalInfo, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, MotorVitalInfo> > >::operator[](std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&)@plt>
  14f569:	f2 0f 10 40 38       	movsd  0x38(%rax),%xmm0
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:172
  14f56e:	f2 0f 11 84 24 98 00 	movsd  %xmm0,0x98(%rsp)
  14f575:	00 00 
  14f577:	4c 89 ef             	mov    %r13,%rdi
  14f57a:	48 8d 74 24 08       	lea    0x8(%rsp),%rsi
  14f57f:	e8 9c 44 f3 ff       	call   83a20 <std::map<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, MotorVitalInfo, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, MotorVitalInfo> > >::operator[](std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&)@plt>
  14f584:	f2 0f 10 40 20       	movsd  0x20(%rax),%xmm0
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:173
  14f589:	f2 0f 11 84 24 d0 00 	movsd  %xmm0,0xd0(%rsp)
  14f590:	00 00 
  14f592:	e8 89 69 f3 ff       	call   85f20 <cos@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:564
  14f597:	48 8b 44 24 30       	mov    0x30(%rsp),%rax
MultiSteersOdometer::CaldPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:173
  14f59c:	f2 0f 59 84 24 98 00 	mulsd  0x98(%rsp),%xmm0
  14f5a3:	00 00 
  14f5a5:	48 8b 9c 24 d8 00 00 	mov    0xd8(%rsp),%rbx
  14f5ac:	00 
  14f5ad:	f2 0f 11 04 18       	movsd  %xmm0,(%rax,%rbx,1)
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:174
  14f5b2:	f2 0f 10 84 24 d0 00 	movsd  0xd0(%rsp),%xmm0
  14f5b9:	00 00 
  14f5bb:	e8 40 4b f3 ff       	call   84100 <sin@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:564
  14f5c0:	48 8b 44 24 30       	mov    0x30(%rsp),%rax
MultiSteersOdometer::CaldPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:174
  14f5c5:	f2 0f 59 84 24 98 00 	mulsd  0x98(%rsp),%xmm0
  14f5cc:	00 00 
  14f5ce:	f2 0f 11 44 18 08    	movsd  %xmm0,0x8(%rax,%rbx,1)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f5d4:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14f5d9:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  14f5de:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14f5e1:	74 05                	je     14f5e8 <MultiSteersOdometer::CaldPose()+0x2e8>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14f5e3:	e8 48 54 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f5e8:	48 8b bc 24 30 01 00 	mov    0x130(%rsp),%rdi
  14f5ef:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14f5f0:	4c 39 e7             	cmp    %r12,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14f5f3:	74 05                	je     14f5fa <MultiSteersOdometer::CaldPose()+0x2fa>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14f5f5:	e8 36 54 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >::operator++(int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:295
  14f5fa:	4c 89 ff             	mov    %r15,%rdi
  14f5fd:	e8 1e 6b f3 ff       	call   86120 <std::_Rb_tree_increment(std::_Rb_tree_node_base*)@plt>
  14f602:	49 89 c7             	mov    %rax,%r15
MultiSteersOdometer::CaldPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:168
  14f605:	48 83 c3 10          	add    $0x10,%rbx
std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >::operator!=(std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:320
  14f609:	4c 3b bc 24 c8 00 00 	cmp    0xc8(%rsp),%r15
  14f610:	00 
MultiSteersOdometer::CaldPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:168
  14f611:	0f 85 09 fe ff ff    	jne    14f420 <MultiSteersOdometer::CaldPose()+0x120>
Eigen::internal::assign_op<double, double>::assignCoeff(double&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/AssignmentFunctors.h:24
  14f617:	66 0f 57 c0          	xorpd  %xmm0,%xmm0
  14f61b:	66 0f 29 84 24 00 01 	movapd %xmm0,0x100(%rsp)
  14f622:	00 00 
  14f624:	48 c7 84 24 10 01 00 	movq   $0x0,0x110(%rsp)
  14f62b:	00 00 00 00 00 
  14f630:	48 8b 5c 24 40       	mov    0x40(%rsp),%rbx
Eigen::DenseStorage<double, -1, -1, -1, 0>::rows() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:394
  14f635:	48 8b bb 98 01 00 00 	mov    0x198(%rbx),%rdi
Eigen::DenseStorage<double, -1, -1, -1, 0>::cols() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:395
  14f63c:	48 8b b3 a0 01 00 00 	mov    0x1a0(%rbx),%rsi
Eigen::DenseStorage<double, -1, -1, -1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:416
  14f643:	48 8b 83 90 01 00 00 	mov    0x190(%rbx),%rax
Eigen::internal::blas_data_mapper<double const, long, 0, 0, 1>::blas_data_mapper(double const*, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/BlasUtil.h:213
  14f64a:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  14f651:	00 
  14f652:	48 89 bc 24 38 01 00 	mov    %rdi,0x138(%rsp)
  14f659:	00 
Eigen::DenseStorage<double, -1, -1, 1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:564
  14f65a:	48 8b 44 24 30       	mov    0x30(%rsp),%rax
Eigen::internal::blas_data_mapper<double const, long, 1, 0, 1>::blas_data_mapper(double const*, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/BlasUtil.h:213
  14f65f:	48 89 44 24 08       	mov    %rax,0x8(%rsp)
  14f664:	48 c7 44 24 10 01 00 	movq   $0x1,0x10(%rsp)
  14f66b:	00 00 
  14f66d:	48 8d 94 24 30 01 00 	lea    0x130(%rsp),%rdx
  14f674:	00 
MultiSteersOdometer::CaldPose():
  14f675:	48 8d 4c 24 08       	lea    0x8(%rsp),%rcx
  14f67a:	4c 8d 84 24 00 01 00 	lea    0x100(%rsp),%r8
  14f681:	00 
void Eigen::internal::gemv_dense_selector<2, 0, true>::run<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, -1, 1, 0, -1, 1>, Eigen::Matrix<double, 3, 1, 0, 3, 1> >(Eigen::Matrix<double, -1, -1, 0, -1, -1> const&, Eigen::Matrix<double, -1, 1, 0, -1, 1> const&, Eigen::Matrix<double, 3, 1, 0, 3, 1>&, Eigen::Matrix<double, 3, 1, 0, 3, 1>::Scalar const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/GeneralProduct.h:243
  14f682:	f2 0f 10 05 ee 91 03 	movsd  0x391ee(%rip),%xmm0        # 188878 <_fini+0x84>
  14f689:	00 
  14f68a:	41 b9 01 00 00 00    	mov    $0x1,%r9d
  14f690:	e8 db 67 f3 ff       	call   85e70 <Eigen::internal::general_matrix_vector_product<long, double, Eigen::internal::const_blas_data_mapper<double, long, 0>, 0, false, double, Eigen::internal::const_blas_data_mapper<double, long, 1>, false, 0>::run(long, long, Eigen::internal::const_blas_data_mapper<double, long, 0> const&, Eigen::internal::const_blas_data_mapper<double, long, 1> const&, double*, long, double)@plt>
MultiSteersOdometer::CaldPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:180
  14f695:	66 0f 28 84 24 00 01 	movapd 0x100(%rsp),%xmm0
  14f69c:	00 00 
  14f69e:	66 0f 11 83 f0 00 00 	movupd %xmm0,0xf0(%rbx)
  14f6a5:	00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:182
  14f6a6:	48 8b 84 24 10 01 00 	mov    0x110(%rsp),%rax
  14f6ad:	00 
  14f6ae:	48 89 83 00 01 00 00 	mov    %rax,0x100(%rbx)
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:184
  14f6b5:	80 7b 0c 00          	cmpb   $0x0,0xc(%rbx)
  14f6b9:	0f 84 ac 04 00 00    	je     14fb6b <MultiSteersOdometer::CaldPose()+0x86b>
  14f6bf:	48 8d bc 24 30 01 00 	lea    0x130(%rsp),%rdi
  14f6c6:	00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:185
  14f6c7:	be 18 00 00 00       	mov    $0x18,%esi
  14f6cc:	e8 ff 4d f3 ff       	call   844d0 <std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::basic_stringstream(std::_Ios_Openmode)@plt>
  14f6d1:	48 8d 9c 24 40 01 00 	lea    0x140(%rsp),%rbx
  14f6d8:	00 
std::basic_ostream<char, std::char_traits<char> >& std::operator<< <std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ostream:561
  14f6d9:	48 8d 35 ab 0b 05 00 	lea    0x50bab(%rip),%rsi        # 1a028b <typeinfo name for rbk::Logger::Thread::move2thread<DualDiffOdometer::CaldPose()::$_4>(DualDiffOdometer::CaldPose()::$_4&&)::{lambda()#1}+0x70b>
  14f6e0:	ba 05 00 00 00       	mov    $0x5,%edx
  14f6e5:	48 89 df             	mov    %rbx,%rdi
  14f6e8:	e8 d3 6a f3 ff       	call   861c0 <std::basic_ostream<char, std::char_traits<char> >& std::__ostream_insert<char, std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*, long)@plt>
MultiSteersOdometer::CaldPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:185
  14f6ed:	48 8d 44 24 30       	lea    0x30(%rsp),%rax
  14f6f2:	48 89 44 24 08       	mov    %rax,0x8(%rsp)
  14f6f7:	48 8d 74 24 08       	lea    0x8(%rsp),%rsi
  14f6fc:	48 89 df             	mov    %rbx,%rdi
  14f6ff:	e8 5c 5f f3 ff       	call   85660 <std::ostream& Eigen::operator<< <Eigen::Transpose<Eigen::Matrix<double, -1, 1, 0, -1, 1> > >(std::ostream&, Eigen::DenseBase<Eigen::Transpose<Eigen::Matrix<double, -1, 1, 0, -1, 1> > > const&)@plt>
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::str() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:779
  14f704:	48 8d b4 24 48 01 00 	lea    0x148(%rsp),%rsi
  14f70b:	00 
  14f70c:	48 8d bc 24 e0 00 00 	lea    0xe0(%rsp),%rdi
  14f713:	00 
  14f714:	e8 e7 4b f3 ff       	call   84300 <std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::str() const@plt>
MultiSteersOdometer::CaldPose():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:185
  14f719:	e8 c2 47 f3 ff       	call   83ee0 <rbk::Logger::thread()@plt>
  14f71e:	49 89 c6             	mov    %rax,%r14
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:182
  14f721:	4c 8d 64 24 68       	lea    0x68(%rsp),%r12
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14f726:	4c 89 64 24 58       	mov    %r12,0x58(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f72b:	4c 8b bc 24 e0 00 00 	mov    0xe0(%rsp),%r15
  14f732:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14f733:	48 8b 9c 24 e8 00 00 	mov    0xe8(%rsp),%rbx
  14f73a:	00 
bool __gnu_cxx::__is_null_pointer<char>(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/type_traits.h:153
  14f73b:	4d 85 ff             	test   %r15,%r15
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:211
  14f73e:	75 09                	jne    14f749 <MultiSteersOdometer::CaldPose()+0x449>
  14f740:	48 85 db             	test   %rbx,%rbx
  14f743:	0f 85 55 04 00 00    	jne    14fb9e <MultiSteersOdometer::CaldPose()+0x89e>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:215
  14f749:	48 89 5c 24 08       	mov    %rbx,0x8(%rsp)
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:217
  14f74e:	48 83 fb 0f          	cmp    $0xf,%rbx
  14f752:	76 4a                	jbe    14f79e <MultiSteersOdometer::CaldPose()+0x49e>
MultiSteersOdometer::CaldPose():
  14f754:	48 8d 7c 24 58       	lea    0x58(%rsp),%rdi
  14f759:	48 8d 74 24 08       	lea    0x8(%rsp),%rsi
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:219
  14f75e:	31 d2                	xor    %edx,%edx
  14f760:	e8 cb 59 f3 ff       	call   85130 <std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_create(unsigned long&, unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14f765:	48 89 44 24 58       	mov    %rax,0x58(%rsp)
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:220
  14f76a:	48 8b 4c 24 08       	mov    0x8(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14f76f:	48 89 4c 24 68       	mov    %rcx,0x68(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  14f774:	48 85 db             	test   %rbx,%rbx
  14f777:	75 2d                	jne    14f7a6 <MultiSteersOdometer::CaldPose()+0x4a6>
  14f779:	eb 46                	jmp    14f7c1 <MultiSteersOdometer::CaldPose()+0x4c1>
MultiSteersOdometer::CaldPose():
  14f77b:	31 c0                	xor    %eax,%eax
  14f77d:	e9 f5 03 00 00       	jmp    14fb77 <MultiSteersOdometer::CaldPose()+0x877>
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:190
  14f782:	66 0f 57 c0          	xorpd  %xmm0,%xmm0
  14f786:	66 0f 11 83 d8 00 00 	movupd %xmm0,0xd8(%rbx)
  14f78d:	00 
  14f78e:	48 c7 83 e8 00 00 00 	movq   $0x0,0xe8(%rbx)
  14f795:	00 00 00 00 
  14f799:	e9 d7 03 00 00       	jmp    14fb75 <MultiSteersOdometer::CaldPose()+0x875>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f79e:	4c 89 e0             	mov    %r12,%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  14f7a1:	48 85 db             	test   %rbx,%rbx
  14f7a4:	74 1b                	je     14f7c1 <MultiSteersOdometer::CaldPose()+0x4c1>
  14f7a6:	48 83 fb 01          	cmp    $0x1,%rbx
  14f7aa:	75 07                	jne    14f7b3 <MultiSteersOdometer::CaldPose()+0x4b3>
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14f7ac:	41 8a 0f             	mov    (%r15),%cl
  14f7af:	88 08                	mov    %cl,(%rax)
  14f7b1:	eb 0e                	jmp    14f7c1 <MultiSteersOdometer::CaldPose()+0x4c1>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14f7b3:	48 89 c7             	mov    %rax,%rdi
  14f7b6:	4c 89 fe             	mov    %r15,%rsi
  14f7b9:	48 89 da             	mov    %rbx,%rdx
  14f7bc:	e8 af 3c f3 ff       	call   83470 <memcpy@plt>
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:232
  14f7c1:	48 8b 44 24 08       	mov    0x8(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14f7c6:	48 89 44 24 60       	mov    %rax,0x60(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f7cb:	48 8b 4c 24 58       	mov    0x58(%rsp),%rcx
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14f7d0:	c6 04 01 00          	movb   $0x0,(%rcx,%rax,1)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:182
  14f7d4:	4c 8d 7c 24 18       	lea    0x18(%rsp),%r15
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14f7d9:	4c 89 7c 24 08       	mov    %r15,0x8(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f7de:	48 8b 5c 24 58       	mov    0x58(%rsp),%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14f7e3:	4c 39 e3             	cmp    %r12,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:534
  14f7e6:	74 11                	je     14f7f9 <MultiSteersOdometer::CaldPose()+0x4f9>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14f7e8:	48 89 5c 24 08       	mov    %rbx,0x8(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:542
  14f7ed:	48 8b 44 24 68       	mov    0x68(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14f7f2:	48 89 44 24 18       	mov    %rax,0x18(%rsp)
  14f7f7:	eb 0e                	jmp    14f807 <MultiSteersOdometer::CaldPose()+0x507>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14f7f9:	66 41 0f 10 04 24    	movupd (%r12),%xmm0
  14f7ff:	66 41 0f 11 07       	movupd %xmm0,(%r15)
  14f804:	4c 89 fb             	mov    %r15,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14f807:	4c 8b 6c 24 60       	mov    0x60(%rsp),%r13
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14f80c:	4c 89 6c 24 10       	mov    %r13,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14f811:	4c 89 64 24 58       	mov    %r12,0x58(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14f816:	48 c7 44 24 60 00 00 	movq   $0x0,0x60(%rsp)
  14f81d:	00 00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14f81f:	c6 44 24 68 00       	movb   $0x0,0x68(%rsp)
std::_Function_base::_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:271
  14f824:	48 c7 84 24 88 00 00 	movq   $0x0,0x88(%rsp)
  14f82b:	00 00 00 00 00 
std::_Function_base::_Base_manager<std::_Bind<MultiSteersOdometer::CaldPose()::$_4 ()> >::_M_init_functor(std::_Any_data&, std::_Bind<MultiSteersOdometer::CaldPose()::$_4 ()>&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14f830:	bf 28 00 00 00       	mov    $0x28,%edi
  14f835:	e8 86 3e f3 ff       	call   836c0 <operator new(unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:182
  14f83a:	48 89 c1             	mov    %rax,%rcx
  14f83d:	48 83 c1 10          	add    $0x10,%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14f841:	48 89 08             	mov    %rcx,(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14f844:	4c 39 fb             	cmp    %r15,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:534
  14f847:	74 0e                	je     14f857 <MultiSteersOdometer::CaldPose()+0x557>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14f849:	48 89 18             	mov    %rbx,(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:542
  14f84c:	48 8b 4c 24 18       	mov    0x18(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14f851:	48 89 48 10          	mov    %rcx,0x10(%rax)
  14f855:	eb 09                	jmp    14f860 <MultiSteersOdometer::CaldPose()+0x560>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14f857:	66 41 0f 10 07       	movupd (%r15),%xmm0
  14f85c:	66 0f 11 01          	movupd %xmm0,(%rcx)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14f860:	4c 89 7c 24 08       	mov    %r15,0x8(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14f865:	48 c7 44 24 10 00 00 	movq   $0x0,0x10(%rsp)
  14f86c:	00 00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14f86e:	c6 44 24 18 00       	movb   $0x0,0x18(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14f873:	4c 89 68 08          	mov    %r13,0x8(%rax)
std::_Function_base::_Base_manager<std::_Bind<MultiSteersOdometer::CaldPose()::$_4 ()> >::_M_init_functor(std::_Any_data&, std::_Bind<MultiSteersOdometer::CaldPose()::$_4 ()>&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14f877:	48 89 44 24 78       	mov    %rax,0x78(%rsp)
std::function<void ()>::function<std::_Bind<MultiSteersOdometer::CaldPose()::$_4 ()>, void, void>(std::_Bind<MultiSteersOdometer::CaldPose()::$_4 ()>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:694
  14f87c:	48 8d 05 7d 17 00 00 	lea    0x177d(%rip),%rax        # 151000 <std::_Function_handler<void (), std::_Bind<MultiSteersOdometer::CaldPose()::$_4 ()> >::_M_invoke(std::_Any_data const&)>
  14f883:	48 89 84 24 90 00 00 	mov    %rax,0x90(%rsp)
  14f88a:	00 
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:695
  14f88b:	48 8d 05 4e 19 00 00 	lea    0x194e(%rip),%rax        # 1511e0 <std::_Function_base::_Base_manager<std::_Bind<MultiSteersOdometer::CaldPose()::$_4 ()> >::_M_manager(std::_Any_data&, std::_Any_data const&, std::_Manager_operation)>
  14f892:	48 89 84 24 88 00 00 	mov    %rax,0x88(%rsp)
  14f899:	00 
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1294
  14f89a:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  14f8a1:	00 00 
  14f8a3:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
MultiSteersOdometer::CaldPose():
  14f8a8:	48 8d 94 24 a0 00 00 	lea    0xa0(%rsp),%rdx
  14f8af:	00 
  14f8b0:	48 8d 4c 24 78       	lea    0x78(%rsp),%rcx
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1294
  14f8b5:	31 f6                	xor    %esi,%esi
  14f8b7:	e8 84 72 f3 ff       	call   86b40 <std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count<std::packaged_task<void ()>, std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::packaged_task<void ()>*, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&)@plt>
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_get_deleter(std::type_info const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:727
  14f8bc:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
  14f8c1:	48 85 ff             	test   %rdi,%rdi
  14f8c4:	74 17                	je     14f8dd <MultiSteersOdometer::CaldPose()+0x5dd>
  14f8c6:	48 8b 07             	mov    (%rdi),%rax
  14f8c9:	48 8b 35 80 7f 2b 00 	mov    0x2b7f80(%rip),%rsi        # 407850 <typeinfo for std::_Sp_make_shared_tag@@Base+0x6d08>
  14f8d0:	ff 50 20             	call   *0x20(%rax)
  14f8d3:	48 89 c3             	mov    %rax,%rbx
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:688
  14f8d6:	4c 8b 7c 24 50       	mov    0x50(%rsp),%r15
  14f8db:	eb 05                	jmp    14f8e2 <MultiSteersOdometer::CaldPose()+0x5e2>
MultiSteersOdometer::CaldPose():
  14f8dd:	45 31 ff             	xor    %r15d,%r15d
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_get_deleter(std::type_info const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:727
  14f8e0:	31 db                	xor    %ebx,%ebx
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1300
  14f8e2:	48 89 5c 24 48       	mov    %rbx,0x48(%rsp)
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:690
  14f8e7:	4d 85 ff             	test   %r15,%r15
  14f8ea:	74 17                	je     14f903 <MultiSteersOdometer::CaldPose()+0x603>
__gnu_cxx::__atomic_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:95
  14f8ec:	48 83 3d b4 81 2b 00 	cmpq   $0x0,0x2b81b4(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14f8f3:	00 
  14f8f4:	74 08                	je     14f8fe <MultiSteersOdometer::CaldPose()+0x5fe>
__gnu_cxx::__atomic_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:53
  14f8f6:	f0 41 83 47 08 01    	lock addl $0x1,0x8(%r15)
  14f8fc:	eb 05                	jmp    14f903 <MultiSteersOdometer::CaldPose()+0x603>
__gnu_cxx::__atomic_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:74
  14f8fe:	41 83 47 08 01       	addl   $0x1,0x8(%r15)
std::_Function_base::_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:271
  14f903:	48 c7 84 24 b0 00 00 	movq   $0x0,0xb0(%rsp)
  14f90a:	00 00 00 00 00 
std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CaldPose()::$_4>(MultiSteersOdometer::CaldPose()::$_4&&)::{lambda()#1}>::_M_init_functor(std::_Any_data&, rbk::Logger::Thread::move2thread<MultiSteersOdometer::CaldPose()::$_4>(MultiSteersOdometer::CaldPose()::$_4&&)::{lambda()#1}&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14f90f:	bf 10 00 00 00       	mov    $0x10,%edi
  14f914:	e8 a7 3d f3 ff       	call   836c0 <operator new(unsigned long)@plt>
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr(std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1131
  14f919:	48 89 18             	mov    %rbx,(%rax)
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_swap(std::__shared_count<(__gnu_cxx::_Lock_policy)2>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:714
  14f91c:	4c 89 78 08          	mov    %r15,0x8(%rax)
std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CaldPose()::$_4>(MultiSteersOdometer::CaldPose()::$_4&&)::{lambda()#1}>::_M_init_functor(std::_Any_data&, rbk::Logger::Thread::move2thread<MultiSteersOdometer::CaldPose()::$_4>(MultiSteersOdometer::CaldPose()::$_4&&)::{lambda()#1}&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14f920:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  14f927:	00 
std::function<void ()>::function<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CaldPose()::$_4>(MultiSteersOdometer::CaldPose()::$_4&&)::{lambda()#1}, void, void>(rbk::Logger::Thread::move2thread<MultiSteersOdometer::CaldPose()::$_4>(MultiSteersOdometer::CaldPose()::$_4&&)::{lambda()#1}):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:694
  14f928:	48 8d 05 e1 19 00 00 	lea    0x19e1(%rip),%rax        # 151310 <std::_Function_handler<void (), rbk::Logger::Thread::move2thread<MultiSteersOdometer::CaldPose()::$_4>(MultiSteersOdometer::CaldPose()::$_4&&)::{lambda()#1}>::_M_invoke(std::_Any_data const&)>
  14f92f:	48 89 84 24 b8 00 00 	mov    %rax,0xb8(%rsp)
  14f936:	00 
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:695
  14f937:	48 8d 05 02 1a 00 00 	lea    0x1a02(%rip),%rax        # 151340 <std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CaldPose()::$_4>(MultiSteersOdometer::CaldPose()::$_4&&)::{lambda()#1}>::_M_manager(std::_Any_data&, std::_Any_data const&, std::_Manager_operation)>
  14f93e:	48 89 84 24 b0 00 00 	mov    %rax,0xb0(%rsp)
  14f945:	00 
std::future<decltype ({parm#1}({parm#2}...))> rbk::Logger::Thread::move2thread<MultiSteersOdometer::CaldPose()::$_4>(MultiSteersOdometer::CaldPose()::$_4&&):
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:204
  14f946:	49 8d 7e 08          	lea    0x8(%r14),%rdi
  14f94a:	48 8d b4 24 a0 00 00 	lea    0xa0(%rsp),%rsi
  14f951:	00 
  14f952:	e8 59 44 f3 ff       	call   83db0 <rbk::Logger::Thread::SafeQueue<std::function<void ()> >::push_back(std::function<void ()>&)@plt>
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:206
  14f957:	49 81 c6 c0 01 00 00 	add    $0x1c0,%r14
  14f95e:	4c 89 f7             	mov    %r14,%rdi
  14f961:	e8 4a 53 f3 ff       	call   84cb0 <std::condition_variable::notify_one()@plt>
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::get() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1258
  14f966:	48 8b 74 24 48       	mov    0x48(%rsp),%rsi
  14f96b:	48 8d bc 24 20 01 00 	lea    0x120(%rsp),%rdi
  14f972:	00 
std::future<decltype ({parm#1}({parm#2}...))> rbk::Logger::Thread::move2thread<MultiSteersOdometer::CaldPose()::$_4>(MultiSteersOdometer::CaldPose()::$_4&&):
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:207
  14f973:	e8 d8 65 f3 ff       	call   85f50 <std::packaged_task<void ()>::get_future()@plt>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14f978:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  14f97f:	00 
  14f980:	48 85 c0             	test   %rax,%rax
  14f983:	74 12                	je     14f997 <MultiSteersOdometer::CaldPose()+0x697>
MultiSteersOdometer::CaldPose():
  14f985:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  14f98c:	00 
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14f98d:	ba 03 00 00 00       	mov    $0x3,%edx
  14f992:	48 89 fe             	mov    %rdi,%rsi
  14f995:	ff d0                	call   *%rax
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14f997:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  14f99c:	48 85 db             	test   %rbx,%rbx
  14f99f:	74 64                	je     14fa05 <MultiSteersOdometer::CaldPose()+0x705>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14f9a1:	48 83 3d ff 80 2b 00 	cmpq   $0x0,0x2b80ff(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14f9a8:	00 
  14f9a9:	74 11                	je     14f9bc <MultiSteersOdometer::CaldPose()+0x6bc>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14f9ab:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14f9b0:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14f9b5:	83 f8 01             	cmp    $0x1,%eax
  14f9b8:	74 10                	je     14f9ca <MultiSteersOdometer::CaldPose()+0x6ca>
  14f9ba:	eb 49                	jmp    14fa05 <MultiSteersOdometer::CaldPose()+0x705>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14f9bc:	8b 43 08             	mov    0x8(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14f9bf:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14f9c2:	89 4b 08             	mov    %ecx,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14f9c5:	83 f8 01             	cmp    $0x1,%eax
  14f9c8:	75 3b                	jne    14fa05 <MultiSteersOdometer::CaldPose()+0x705>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14f9ca:	48 8b 03             	mov    (%rbx),%rax
  14f9cd:	48 89 df             	mov    %rbx,%rdi
  14f9d0:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14f9d3:	48 83 3d cd 80 2b 00 	cmpq   $0x0,0x2b80cd(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14f9da:	00 
  14f9db:	74 11                	je     14f9ee <MultiSteersOdometer::CaldPose()+0x6ee>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14f9dd:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14f9e2:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14f9e7:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14f9ea:	74 10                	je     14f9fc <MultiSteersOdometer::CaldPose()+0x6fc>
  14f9ec:	eb 17                	jmp    14fa05 <MultiSteersOdometer::CaldPose()+0x705>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14f9ee:	8b 43 0c             	mov    0xc(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14f9f1:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14f9f4:	89 4b 0c             	mov    %ecx,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14f9f7:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14f9fa:	75 09                	jne    14fa05 <MultiSteersOdometer::CaldPose()+0x705>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14f9fc:	48 8b 03             	mov    (%rbx),%rax
  14f9ff:	48 89 df             	mov    %rbx,%rdi
  14fa02:	ff 50 18             	call   *0x18(%rax)
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14fa05:	48 8b 84 24 88 00 00 	mov    0x88(%rsp),%rax
  14fa0c:	00 
  14fa0d:	48 85 c0             	test   %rax,%rax
  14fa10:	74 0f                	je     14fa21 <MultiSteersOdometer::CaldPose()+0x721>
MultiSteersOdometer::CaldPose():
  14fa12:	48 8d 7c 24 78       	lea    0x78(%rsp),%rdi
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14fa17:	ba 03 00 00 00       	mov    $0x3,%edx
  14fa1c:	48 89 fe             	mov    %rdi,%rsi
  14fa1f:	ff d0                	call   *%rax
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14fa21:	48 8b 9c 24 28 01 00 	mov    0x128(%rsp),%rbx
  14fa28:	00 
  14fa29:	48 85 db             	test   %rbx,%rbx
  14fa2c:	74 64                	je     14fa92 <MultiSteersOdometer::CaldPose()+0x792>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14fa2e:	48 83 3d 72 80 2b 00 	cmpq   $0x0,0x2b8072(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14fa35:	00 
  14fa36:	74 11                	je     14fa49 <MultiSteersOdometer::CaldPose()+0x749>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14fa38:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14fa3d:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14fa42:	83 f8 01             	cmp    $0x1,%eax
  14fa45:	74 10                	je     14fa57 <MultiSteersOdometer::CaldPose()+0x757>
  14fa47:	eb 49                	jmp    14fa92 <MultiSteersOdometer::CaldPose()+0x792>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14fa49:	8b 43 08             	mov    0x8(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14fa4c:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14fa4f:	89 4b 08             	mov    %ecx,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14fa52:	83 f8 01             	cmp    $0x1,%eax
  14fa55:	75 3b                	jne    14fa92 <MultiSteersOdometer::CaldPose()+0x792>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14fa57:	48 8b 03             	mov    (%rbx),%rax
  14fa5a:	48 89 df             	mov    %rbx,%rdi
  14fa5d:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14fa60:	48 83 3d 40 80 2b 00 	cmpq   $0x0,0x2b8040(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14fa67:	00 
  14fa68:	74 11                	je     14fa7b <MultiSteersOdometer::CaldPose()+0x77b>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14fa6a:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14fa6f:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14fa74:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14fa77:	74 10                	je     14fa89 <MultiSteersOdometer::CaldPose()+0x789>
  14fa79:	eb 17                	jmp    14fa92 <MultiSteersOdometer::CaldPose()+0x792>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14fa7b:	8b 43 0c             	mov    0xc(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14fa7e:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14fa81:	89 4b 0c             	mov    %ecx,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14fa84:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14fa87:	75 09                	jne    14fa92 <MultiSteersOdometer::CaldPose()+0x792>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14fa89:	48 8b 03             	mov    (%rbx),%rax
  14fa8c:	48 89 df             	mov    %rbx,%rdi
  14fa8f:	ff 50 18             	call   *0x18(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14fa92:	48 8b 7c 24 58       	mov    0x58(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14fa97:	4c 39 e7             	cmp    %r12,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14fa9a:	74 05                	je     14faa1 <MultiSteersOdometer::CaldPose()+0x7a1>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14fa9c:	e8 8f 4f f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14faa1:	48 8b bc 24 e0 00 00 	mov    0xe0(%rsp),%rdi
  14faa8:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14faa9:	48 8d 84 24 f0 00 00 	lea    0xf0(%rsp),%rax
  14fab0:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14fab1:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14fab4:	74 05                	je     14fabb <MultiSteersOdometer::CaldPose()+0x7bb>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14fab6:	e8 75 4f f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::~basic_stringstream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:731
  14fabb:	48 8b 1d a6 7f 2b 00 	mov    0x2b7fa6(%rip),%rbx        # 407a68 <VTT for std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  14fac2:	48 8b 03             	mov    (%rbx),%rax
  14fac5:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  14facc:	00 
  14facd:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  14fad1:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14fad5:	48 89 8c 04 30 01 00 	mov    %rcx,0x130(%rsp,%rax,1)
  14fadc:	00 
  14fadd:	48 8b 43 48          	mov    0x48(%rbx),%rax
  14fae1:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  14fae8:	00 
std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::~basic_stringbuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/sstream.tcc:291
  14fae9:	48 8b 05 78 73 2b 00 	mov    0x2b7378(%rip),%rax        # 406e68 <vtable for std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  14faf0:	48 83 c0 10          	add    $0x10,%rax
  14faf4:	48 89 84 24 48 01 00 	mov    %rax,0x148(%rsp)
  14fafb:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14fafc:	48 8b bc 24 90 01 00 	mov    0x190(%rsp),%rdi
  14fb03:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14fb04:	48 8d 84 24 a0 01 00 	lea    0x1a0(%rsp),%rax
  14fb0b:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14fb0c:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14fb0f:	74 05                	je     14fb16 <MultiSteersOdometer::CaldPose()+0x816>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14fb11:	e8 1a 4f f3 ff       	call   84a30 <operator delete(void*)@plt>
std::basic_streambuf<char, std::char_traits<char> >::~basic_streambuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/streambuf:198
  14fb16:	48 8b 05 fb 7d 2b 00 	mov    0x2b7dfb(%rip),%rax        # 407918 <vtable for std::basic_streambuf<char, std::char_traits<char> >@GLIBCXX_3.4>
  14fb1d:	48 83 c0 10          	add    $0x10,%rax
  14fb21:	48 89 84 24 48 01 00 	mov    %rax,0x148(%rsp)
  14fb28:	00 
  14fb29:	48 8d bc 24 80 01 00 	lea    0x180(%rsp),%rdi
  14fb30:	00 
  14fb31:	e8 fa 66 f3 ff       	call   86230 <std::locale::~locale()@plt>
std::basic_istream<char, std::char_traits<char> >::~basic_istream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/istream:104
  14fb36:	48 8b 43 10          	mov    0x10(%rbx),%rax
  14fb3a:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  14fb3e:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  14fb45:	00 
  14fb46:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14fb4a:	48 89 8c 04 30 01 00 	mov    %rcx,0x130(%rsp,%rax,1)
  14fb51:	00 
  14fb52:	48 c7 84 24 38 01 00 	movq   $0x0,0x138(%rsp)
  14fb59:	00 00 00 00 00 
std::basic_ios<char, std::char_traits<char> >::~basic_ios():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:282
  14fb5e:	48 8d bc 24 b0 01 00 	lea    0x1b0(%rsp),%rdi
  14fb65:	00 
  14fb66:	e8 b5 57 f3 ff       	call   85320 <std::ios_base::~ios_base()@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::~DenseStorage():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:542
  14fb6b:	48 8b 7c 24 30       	mov    0x30(%rsp),%rdi
Eigen::internal::aligned_free(void*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:177
  14fb70:	e8 fb 3b f3 ff       	call   83770 <free@plt>
MultiSteersOdometer::CaldPose():
  14fb75:	b0 01                	mov    $0x1,%al
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:195
  14fb77:	48 8d 65 d8          	lea    -0x28(%rbp),%rsp
  14fb7b:	5b                   	pop    %rbx
  14fb7c:	41 5c                	pop    %r12
  14fb7e:	41 5d                	pop    %r13
  14fb80:	41 5e                	pop    %r14
  14fb82:	41 5f                	pop    %r15
  14fb84:	5d                   	pop    %rbp
  14fb85:	c3                   	ret    
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:212
  14fb86:	48 8d 3d 28 df 03 00 	lea    0x3df28(%rip),%rdi        # 18dab5 <typeinfo name for rbk::Logger::Thread::move2thread<OdoCalculator::run()::$_32>(OdoCalculator::run()::$_32&&)::{lambda()#1}+0x1755>
  14fb8d:	e8 9e 37 f3 ff       	call   83330 <std::__throw_logic_error(char const*)@plt>
  14fb92:	48 8d 3d 1c df 03 00 	lea    0x3df1c(%rip),%rdi        # 18dab5 <typeinfo name for rbk::Logger::Thread::move2thread<OdoCalculator::run()::$_32>(OdoCalculator::run()::$_32&&)::{lambda()#1}+0x1755>
  14fb99:	e8 92 37 f3 ff       	call   83330 <std::__throw_logic_error(char const*)@plt>
  14fb9e:	48 8d 3d 10 df 03 00 	lea    0x3df10(%rip),%rdi        # 18dab5 <typeinfo name for rbk::Logger::Thread::move2thread<OdoCalculator::run()::$_32>(OdoCalculator::run()::$_32&&)::{lambda()#1}+0x1755>
  14fba5:	e8 86 37 f3 ff       	call   83330 <std::__throw_logic_error(char const*)@plt>
MultiSteersOdometer::CaldPose():
  14fbaa:	e9 88 02 00 00       	jmp    14fe37 <MultiSteersOdometer::CaldPose()+0xb37>
  14fbaf:	49 89 c5             	mov    %rax,%r13
  14fbb2:	e9 9e 02 00 00       	jmp    14fe55 <MultiSteersOdometer::CaldPose()+0xb55>
  14fbb7:	e9 b3 00 00 00       	jmp    14fc6f <MultiSteersOdometer::CaldPose()+0x96f>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14fbbc:	48 89 c7             	mov    %rax,%rdi
  14fbbf:	e8 dc 71 f5 ff       	call   a6da0 <__clang_call_terminate>
  14fbc4:	48 89 c7             	mov    %rax,%rdi
  14fbc7:	e8 d4 71 f5 ff       	call   a6da0 <__clang_call_terminate>
MultiSteersOdometer::CaldPose():
  14fbcc:	49 89 c5             	mov    %rax,%r13
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:690
  14fbcf:	4d 85 ff             	test   %r15,%r15
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14fbd2:	0f 84 e3 00 00 00    	je     14fcbb <MultiSteersOdometer::CaldPose()+0x9bb>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14fbd8:	48 83 3d c8 7e 2b 00 	cmpq   $0x0,0x2b7ec8(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14fbdf:	00 
  14fbe0:	74 15                	je     14fbf7 <MultiSteersOdometer::CaldPose()+0x8f7>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14fbe2:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14fbe7:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14fbed:	83 f8 01             	cmp    $0x1,%eax
  14fbf0:	74 19                	je     14fc0b <MultiSteersOdometer::CaldPose()+0x90b>
  14fbf2:	e9 c4 00 00 00       	jmp    14fcbb <MultiSteersOdometer::CaldPose()+0x9bb>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14fbf7:	41 8b 47 08          	mov    0x8(%r15),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14fbfb:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14fbfe:	41 89 4f 08          	mov    %ecx,0x8(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14fc02:	83 f8 01             	cmp    $0x1,%eax
  14fc05:	0f 85 b0 00 00 00    	jne    14fcbb <MultiSteersOdometer::CaldPose()+0x9bb>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14fc0b:	49 8b 07             	mov    (%r15),%rax
  14fc0e:	4c 89 ff             	mov    %r15,%rdi
  14fc11:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14fc14:	48 83 3d 8c 7e 2b 00 	cmpq   $0x0,0x2b7e8c(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14fc1b:	00 
  14fc1c:	74 15                	je     14fc33 <MultiSteersOdometer::CaldPose()+0x933>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14fc1e:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14fc23:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14fc29:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14fc2c:	74 15                	je     14fc43 <MultiSteersOdometer::CaldPose()+0x943>
  14fc2e:	e9 88 00 00 00       	jmp    14fcbb <MultiSteersOdometer::CaldPose()+0x9bb>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14fc33:	41 8b 47 0c          	mov    0xc(%r15),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14fc37:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14fc3a:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14fc3e:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14fc41:	75 78                	jne    14fcbb <MultiSteersOdometer::CaldPose()+0x9bb>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14fc43:	49 8b 07             	mov    (%r15),%rax
  14fc46:	4c 89 ff             	mov    %r15,%rdi
  14fc49:	ff 50 18             	call   *0x18(%rax)
  14fc4c:	eb 6d                	jmp    14fcbb <MultiSteersOdometer::CaldPose()+0x9bb>
MultiSteersOdometer::CaldPose():
  14fc4e:	49 89 c5             	mov    %rax,%r13
  14fc51:	e9 d3 00 00 00       	jmp    14fd29 <MultiSteersOdometer::CaldPose()+0xa29>
  14fc56:	49 89 c5             	mov    %rax,%r13
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14fc59:	4c 39 fb             	cmp    %r15,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14fc5c:	0f 84 e3 00 00 00    	je     14fd45 <MultiSteersOdometer::CaldPose()+0xa45>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14fc62:	48 89 df             	mov    %rbx,%rdi
  14fc65:	e8 c6 4d f3 ff       	call   84a30 <operator delete(void*)@plt>
  14fc6a:	e9 d6 00 00 00       	jmp    14fd45 <MultiSteersOdometer::CaldPose()+0xa45>
MultiSteersOdometer::CaldPose():
  14fc6f:	49 89 c5             	mov    %rax,%r13
  14fc72:	e9 dd 00 00 00       	jmp    14fd54 <MultiSteersOdometer::CaldPose()+0xa54>
  14fc77:	49 89 c5             	mov    %rax,%r13
  14fc7a:	e9 ef 00 00 00       	jmp    14fd6e <MultiSteersOdometer::CaldPose()+0xa6e>
  14fc7f:	49 89 c5             	mov    %rax,%r13
  14fc82:	e9 e7 00 00 00       	jmp    14fd6e <MultiSteersOdometer::CaldPose()+0xa6e>
  14fc87:	49 89 c5             	mov    %rax,%r13
  14fc8a:	e9 df 00 00 00       	jmp    14fd6e <MultiSteersOdometer::CaldPose()+0xa6e>
  14fc8f:	e9 a3 01 00 00       	jmp    14fe37 <MultiSteersOdometer::CaldPose()+0xb37>
  14fc94:	e9 9e 01 00 00       	jmp    14fe37 <MultiSteersOdometer::CaldPose()+0xb37>
  14fc99:	49 89 c5             	mov    %rax,%r13
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14fc9c:	48 8b 8c 24 b0 00 00 	mov    0xb0(%rsp),%rcx
  14fca3:	00 
  14fca4:	48 85 c9             	test   %rcx,%rcx
  14fca7:	74 12                	je     14fcbb <MultiSteersOdometer::CaldPose()+0x9bb>
MultiSteersOdometer::CaldPose():
  14fca9:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  14fcb0:	00 
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14fcb1:	ba 03 00 00 00       	mov    $0x3,%edx
  14fcb6:	48 89 fe             	mov    %rdi,%rsi
  14fcb9:	ff d1                	call   *%rcx
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14fcbb:	48 8b 5c 24 50       	mov    0x50(%rsp),%rbx
  14fcc0:	48 85 db             	test   %rbx,%rbx
  14fcc3:	74 64                	je     14fd29 <MultiSteersOdometer::CaldPose()+0xa29>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14fcc5:	48 83 3d db 7d 2b 00 	cmpq   $0x0,0x2b7ddb(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14fccc:	00 
  14fccd:	74 11                	je     14fce0 <MultiSteersOdometer::CaldPose()+0x9e0>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14fccf:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14fcd4:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14fcd9:	83 f8 01             	cmp    $0x1,%eax
  14fcdc:	74 10                	je     14fcee <MultiSteersOdometer::CaldPose()+0x9ee>
  14fcde:	eb 49                	jmp    14fd29 <MultiSteersOdometer::CaldPose()+0xa29>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14fce0:	8b 43 08             	mov    0x8(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14fce3:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14fce6:	89 4b 08             	mov    %ecx,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14fce9:	83 f8 01             	cmp    $0x1,%eax
  14fcec:	75 3b                	jne    14fd29 <MultiSteersOdometer::CaldPose()+0xa29>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14fcee:	48 8b 03             	mov    (%rbx),%rax
  14fcf1:	48 89 df             	mov    %rbx,%rdi
  14fcf4:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14fcf7:	48 83 3d a9 7d 2b 00 	cmpq   $0x0,0x2b7da9(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14fcfe:	00 
  14fcff:	74 11                	je     14fd12 <MultiSteersOdometer::CaldPose()+0xa12>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14fd01:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14fd06:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14fd0b:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14fd0e:	74 10                	je     14fd20 <MultiSteersOdometer::CaldPose()+0xa20>
  14fd10:	eb 17                	jmp    14fd29 <MultiSteersOdometer::CaldPose()+0xa29>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14fd12:	8b 43 0c             	mov    0xc(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14fd15:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14fd18:	89 4b 0c             	mov    %ecx,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14fd1b:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14fd1e:	75 09                	jne    14fd29 <MultiSteersOdometer::CaldPose()+0xa29>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14fd20:	48 8b 03             	mov    (%rbx),%rax
  14fd23:	48 89 df             	mov    %rbx,%rdi
  14fd26:	ff 50 18             	call   *0x18(%rax)
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14fd29:	48 8b 8c 24 88 00 00 	mov    0x88(%rsp),%rcx
  14fd30:	00 
  14fd31:	48 85 c9             	test   %rcx,%rcx
  14fd34:	74 0f                	je     14fd45 <MultiSteersOdometer::CaldPose()+0xa45>
MultiSteersOdometer::CaldPose():
  14fd36:	48 8d 7c 24 78       	lea    0x78(%rsp),%rdi
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14fd3b:	ba 03 00 00 00       	mov    $0x3,%edx
  14fd40:	48 89 fe             	mov    %rdi,%rsi
  14fd43:	ff d1                	call   *%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14fd45:	48 8b 7c 24 58       	mov    0x58(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14fd4a:	4c 39 e7             	cmp    %r12,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14fd4d:	74 05                	je     14fd54 <MultiSteersOdometer::CaldPose()+0xa54>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14fd4f:	e8 dc 4c f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14fd54:	48 8b bc 24 e0 00 00 	mov    0xe0(%rsp),%rdi
  14fd5b:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14fd5c:	48 8d 84 24 f0 00 00 	lea    0xf0(%rsp),%rax
  14fd63:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14fd64:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14fd67:	74 05                	je     14fd6e <MultiSteersOdometer::CaldPose()+0xa6e>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14fd69:	e8 c2 4c f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::~basic_stringstream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:731
  14fd6e:	48 8b 1d f3 7c 2b 00 	mov    0x2b7cf3(%rip),%rbx        # 407a68 <VTT for std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  14fd75:	48 8b 03             	mov    (%rbx),%rax
  14fd78:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  14fd7f:	00 
  14fd80:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  14fd84:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14fd88:	48 89 8c 04 30 01 00 	mov    %rcx,0x130(%rsp,%rax,1)
  14fd8f:	00 
  14fd90:	48 8b 43 48          	mov    0x48(%rbx),%rax
  14fd94:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  14fd9b:	00 
std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::~basic_stringbuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/sstream.tcc:291
  14fd9c:	48 8b 05 c5 70 2b 00 	mov    0x2b70c5(%rip),%rax        # 406e68 <vtable for std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  14fda3:	48 83 c0 10          	add    $0x10,%rax
  14fda7:	48 89 84 24 48 01 00 	mov    %rax,0x148(%rsp)
  14fdae:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14fdaf:	48 8b bc 24 90 01 00 	mov    0x190(%rsp),%rdi
  14fdb6:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14fdb7:	48 8d 84 24 a0 01 00 	lea    0x1a0(%rsp),%rax
  14fdbe:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14fdbf:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14fdc2:	74 05                	je     14fdc9 <MultiSteersOdometer::CaldPose()+0xac9>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14fdc4:	e8 67 4c f3 ff       	call   84a30 <operator delete(void*)@plt>
std::basic_streambuf<char, std::char_traits<char> >::~basic_streambuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/streambuf:198
  14fdc9:	48 8b 05 48 7b 2b 00 	mov    0x2b7b48(%rip),%rax        # 407918 <vtable for std::basic_streambuf<char, std::char_traits<char> >@GLIBCXX_3.4>
  14fdd0:	48 83 c0 10          	add    $0x10,%rax
  14fdd4:	48 89 84 24 48 01 00 	mov    %rax,0x148(%rsp)
  14fddb:	00 
  14fddc:	48 8d bc 24 80 01 00 	lea    0x180(%rsp),%rdi
  14fde3:	00 
  14fde4:	e8 47 64 f3 ff       	call   86230 <std::locale::~locale()@plt>
std::basic_istream<char, std::char_traits<char> >::~basic_istream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/istream:104
  14fde9:	48 8b 43 10          	mov    0x10(%rbx),%rax
  14fded:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  14fdf1:	48 89 84 24 30 01 00 	mov    %rax,0x130(%rsp)
  14fdf8:	00 
  14fdf9:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14fdfd:	48 89 8c 04 30 01 00 	mov    %rcx,0x130(%rsp,%rax,1)
  14fe04:	00 
  14fe05:	48 c7 84 24 38 01 00 	movq   $0x0,0x138(%rsp)
  14fe0c:	00 00 00 00 00 
std::basic_ios<char, std::char_traits<char> >::~basic_ios():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:282
  14fe11:	48 8d bc 24 b0 01 00 	lea    0x1b0(%rsp),%rdi
  14fe18:	00 
  14fe19:	e8 02 55 f3 ff       	call   85320 <std::ios_base::~ios_base()@plt>
  14fe1e:	eb 47                	jmp    14fe67 <MultiSteersOdometer::CaldPose()+0xb67>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14fe20:	48 89 c7             	mov    %rax,%rdi
  14fe23:	e8 78 6f f5 ff       	call   a6da0 <__clang_call_terminate>
  14fe28:	48 89 c7             	mov    %rax,%rdi
  14fe2b:	e8 70 6f f5 ff       	call   a6da0 <__clang_call_terminate>
MultiSteersOdometer::CaldPose():
  14fe30:	eb 05                	jmp    14fe37 <MultiSteersOdometer::CaldPose()+0xb37>
  14fe32:	49 89 c5             	mov    %rax,%r13
  14fe35:	eb 1e                	jmp    14fe55 <MultiSteersOdometer::CaldPose()+0xb55>
  14fe37:	49 89 c5             	mov    %rax,%r13
  14fe3a:	eb 2b                	jmp    14fe67 <MultiSteersOdometer::CaldPose()+0xb67>
  14fe3c:	eb 00                	jmp    14fe3e <MultiSteersOdometer::CaldPose()+0xb3e>
  14fe3e:	49 89 c5             	mov    %rax,%r13
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14fe41:	48 8b 7c 24 08       	mov    0x8(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14fe46:	48 8d 44 24 18       	lea    0x18(%rsp),%rax
  14fe4b:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14fe4e:	74 05                	je     14fe55 <MultiSteersOdometer::CaldPose()+0xb55>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14fe50:	e8 db 4b f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14fe55:	48 8b bc 24 30 01 00 	mov    0x130(%rsp),%rdi
  14fe5c:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14fe5d:	4c 39 e7             	cmp    %r12,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14fe60:	74 05                	je     14fe67 <MultiSteersOdometer::CaldPose()+0xb67>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14fe62:	e8 c9 4b f3 ff       	call   84a30 <operator delete(void*)@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::~DenseStorage():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:542
  14fe67:	48 8b 7c 24 30       	mov    0x30(%rsp),%rdi
Eigen::internal::aligned_free(void*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:177
  14fe6c:	e8 ff 38 f3 ff       	call   83770 <free@plt>
MultiSteersOdometer::CaldPose():
  14fe71:	4c 89 ef             	mov    %r13,%rdi
  14fe74:	e8 07 51 f3 ff       	call   84f80 <_Unwind_Resume@plt>
  14fe79:	0f 1f 80 00 00 00 00 	nopl   0x0(%rax)
