
/media/amap/6ab6980d-f090-4387-8753-a2251e75651d/usr/local/SeerRobotics/rbk/plugins/libOdoCalculator.so:     file format elf64-x86-64


Disassembly of section .text:

000000000014d690 <MultiSteersOdometer::CalSpeed()>:
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:110
  14d690:	55                   	push   %rbp
  14d691:	48 89 e5             	mov    %rsp,%rbp
  14d694:	41 57                	push   %r15
  14d696:	41 56                	push   %r14
  14d698:	41 55                	push   %r13
  14d69a:	41 54                	push   %r12
  14d69c:	53                   	push   %rbx
  14d69d:	48 83 e4 f0          	and    $0xfffffffffffffff0,%rsp
  14d6a1:	48 81 ec f0 02 00 00 	sub    $0x2f0,%rsp
  14d6a8:	48 89 fb             	mov    %rdi,%rbx
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:111
  14d6ab:	e8 a0 5e f3 ff       	call   83550 <AbstractOdometer::CalSpeed()@plt>
  14d6b0:	84 c0                	test   %al,%al
  14d6b2:	0f 84 59 04 00 00    	je     14db11 <MultiSteersOdometer::CalSpeed()+0x481>
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:114
  14d6b8:	80 7b 0b 00          	cmpb   $0x0,0xb(%rbx)
  14d6bc:	0f 84 56 04 00 00    	je     14db18 <MultiSteersOdometer::CalSpeed()+0x488>
std::_Rb_tree<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::_Select1st<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > >::size() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:997
  14d6c2:	4c 8b bb 70 01 00 00 	mov    0x170(%rbx),%r15
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:117
  14d6c9:	4d 01 ff             	add    %r15,%r15
Eigen::DenseStorage<double, -1, -1, 1, 0>::DenseStorage():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:500
  14d6cc:	66 0f 57 c0          	xorpd  %xmm0,%xmm0
  14d6d0:	66 0f 29 44 24 70    	movapd %xmm0,0x70(%rsp)
MultiSteersOdometer::CalSpeed():
  14d6d6:	48 8d 7c 24 70       	lea    0x70(%rsp),%rdi
void Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> >::resizeLike<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >(Eigen::EigenBase<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > > const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/PlainObjectBase.h:375
  14d6db:	ba 01 00 00 00       	mov    $0x1,%edx
  14d6e0:	4c 89 fe             	mov    %r15,%rsi
  14d6e3:	e8 78 74 f3 ff       	call   84b60 <Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> >::resize(long, long)@plt>
void Eigen::internal::resize_if_allowed<Eigen::Matrix<double, -1, 1, 0, -1, 1>, Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> >, double, double>(Eigen::Matrix<double, -1, 1, 0, -1, 1>&, Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > const&, Eigen::internal::assign_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:719
  14d6e8:	4c 39 7c 24 78       	cmp    %r15,0x78(%rsp)
  14d6ed:	48 89 5c 24 38       	mov    %rbx,0x38(%rsp)
  14d6f2:	74 17                	je     14d70b <MultiSteersOdometer::CalSpeed()+0x7b>
MultiSteersOdometer::CalSpeed():
  14d6f4:	48 8d 7c 24 70       	lea    0x70(%rsp),%rdi
void Eigen::internal::resize_if_allowed<Eigen::Matrix<double, -1, 1, 0, -1, 1>, Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> >, double, double>(Eigen::Matrix<double, -1, 1, 0, -1, 1>&, Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > const&, Eigen::internal::assign_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:720
  14d6f9:	ba 01 00 00 00       	mov    $0x1,%edx
  14d6fe:	4c 89 fe             	mov    %r15,%rsi
  14d701:	e8 5a 74 f3 ff       	call   84b60 <Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> >::resize(long, long)@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::rows() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:544
  14d706:	4c 8b 7c 24 78       	mov    0x78(%rsp),%r15
Eigen::DenseStorage<double, -1, -1, 1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:564
  14d70b:	4c 8b 74 24 70       	mov    0x70(%rsp),%r14
Eigen::internal::dense_assignment_loop<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >, Eigen::internal::assign_op<double, double>, 0>, 3, 0>::run(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >, Eigen::internal::assign_op<double, double>, 0>&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:411
  14d710:	4c 89 fb             	mov    %r15,%rbx
  14d713:	48 c1 eb 3f          	shr    $0x3f,%rbx
  14d717:	4c 01 fb             	add    %r15,%rbx
  14d71a:	49 89 dc             	mov    %rbx,%r12
  14d71d:	49 83 e4 fe          	and    $0xfffffffffffffffe,%r12
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14d721:	49 83 ff 02          	cmp    $0x2,%r15
  14d725:	7c 39                	jl     14d760 <MultiSteersOdometer::CalSpeed()+0xd0>
  14d727:	49 83 fc 01          	cmp    $0x1,%r12
  14d72b:	b8 02 00 00 00       	mov    $0x2,%eax
  14d730:	49 0f 4f c4          	cmovg  %r12,%rax
  14d734:	48 b9 ff ff ff ff ff 	movabs $0x1fffffffffffffff,%rcx
  14d73b:	ff ff 1f 
  14d73e:	48 01 c1             	add    %rax,%rcx
  14d741:	48 b8 fe ff ff ff ff 	movabs $0x1ffffffffffffffe,%rax
  14d748:	ff ff 1f 
  14d74b:	48 21 c8             	and    %rcx,%rax
  14d74e:	48 8d 14 c5 10 00 00 	lea    0x10(,%rax,8),%rdx
  14d755:	00 
void Eigen::internal::pstore<double, double __vector(2)>(double*, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:359
  14d756:	31 f6                	xor    %esi,%esi
  14d758:	4c 89 f7             	mov    %r14,%rdi
  14d75b:	e8 20 67 f3 ff       	call   83e80 <memset@plt>
MultiSteersOdometer::CalSpeed():
  14d760:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  14d765:	4c 8d a8 48 01 00 00 	lea    0x148(%rax),%r13
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >, Eigen::internal::assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >, Eigen::internal::assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14d76c:	4d 39 fc             	cmp    %r15,%r12
  14d76f:	7d 1c                	jge    14d78d <MultiSteersOdometer::CalSpeed()+0xfd>
MultiSteersOdometer::CalSpeed():
  14d771:	48 d1 fb             	sar    %rbx
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >, Eigen::internal::assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> > >, Eigen::internal::assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14d774:	4b 8d 3c e6          	lea    (%r14,%r12,8),%rdi
  14d778:	49 c1 e7 03          	shl    $0x3,%r15
  14d77c:	48 c1 e3 04          	shl    $0x4,%rbx
  14d780:	49 29 df             	sub    %rbx,%r15
Eigen::internal::assign_op<double, double>::assignCoeff(double&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/AssignmentFunctors.h:24
  14d783:	31 f6                	xor    %esi,%esi
  14d785:	4c 89 fa             	mov    %r15,%rdx
  14d788:	e8 f3 66 f3 ff       	call   83e80 <memset@plt>
std::_Rb_tree<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::_Select1st<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > >::begin():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:961
  14d78d:	4d 8b 75 18          	mov    0x18(%r13),%r14
std::_Rb_tree<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::_Select1st<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > >::end():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:969
  14d791:	49 83 c5 08          	add    $0x8,%r13
  14d795:	4c 89 ac 24 88 00 00 	mov    %r13,0x88(%rsp)
  14d79c:	00 
std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >::operator!=(std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:320
  14d79d:	4d 39 ee             	cmp    %r13,%r14
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:119
  14d7a0:	0f 84 1b 02 00 00    	je     14d9c1 <MultiSteersOdometer::CalSpeed()+0x331>
  14d7a6:	4c 8d a4 24 50 01 00 	lea    0x150(%rsp),%r12
  14d7ad:	00 
  14d7ae:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  14d7b3:	4c 8d 78 40          	lea    0x40(%rax),%r15
  14d7b7:	31 db                	xor    %ebx,%ebx
  14d7b9:	4c 89 bc 24 e8 00 00 	mov    %r15,0xe8(%rsp)
  14d7c0:	00 
  14d7c1:	66 66 66 66 66 66 2e 	data16 data16 data16 data16 data16 cs nopw 0x0(%rax,%rax,1)
  14d7c8:	0f 1f 84 00 00 00 00 
  14d7cf:	00 
  14d7d0:	48 89 9c 24 98 00 00 	mov    %rbx,0x98(%rsp)
  14d7d7:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14d7d8:	4c 89 a4 24 40 01 00 	mov    %r12,0x140(%rsp)
  14d7df:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d7e0:	4d 8b 7e 20          	mov    0x20(%r14),%r15
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14d7e4:	4d 8b 6e 28          	mov    0x28(%r14),%r13
bool __gnu_cxx::__is_null_pointer<char>(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/type_traits.h:153
  14d7e8:	4d 85 ff             	test   %r15,%r15
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:211
  14d7eb:	75 09                	jne    14d7f6 <MultiSteersOdometer::CalSpeed()+0x166>
  14d7ed:	4d 85 ed             	test   %r13,%r13
  14d7f0:	0f 85 e6 14 00 00    	jne    14ecdc <MultiSteersOdometer::CalSpeed()+0x164c>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:215
  14d7f6:	4c 89 6c 24 10       	mov    %r13,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d7fb:	4c 89 e0             	mov    %r12,%rax
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:217
  14d7fe:	49 83 fd 10          	cmp    $0x10,%r13
  14d802:	72 29                	jb     14d82d <MultiSteersOdometer::CalSpeed()+0x19d>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:219
  14d804:	31 d2                	xor    %edx,%edx
  14d806:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  14d80d:	00 
  14d80e:	48 8d 74 24 10       	lea    0x10(%rsp),%rsi
  14d813:	e8 18 79 f3 ff       	call   85130 <std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_create(unsigned long&, unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14d818:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  14d81f:	00 
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:220
  14d820:	48 8b 4c 24 10       	mov    0x10(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14d825:	48 89 8c 24 50 01 00 	mov    %rcx,0x150(%rsp)
  14d82c:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  14d82d:	4d 85 ed             	test   %r13,%r13
  14d830:	74 1c                	je     14d84e <MultiSteersOdometer::CalSpeed()+0x1be>
  14d832:	49 83 fd 01          	cmp    $0x1,%r13
  14d836:	75 08                	jne    14d840 <MultiSteersOdometer::CalSpeed()+0x1b0>
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14d838:	41 0f b6 0f          	movzbl (%r15),%ecx
  14d83c:	88 08                	mov    %cl,(%rax)
  14d83e:	eb 0e                	jmp    14d84e <MultiSteersOdometer::CalSpeed()+0x1be>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14d840:	48 89 c7             	mov    %rax,%rdi
  14d843:	4c 89 fe             	mov    %r15,%rsi
  14d846:	4c 89 ea             	mov    %r13,%rdx
  14d849:	e8 22 5c f3 ff       	call   83470 <memcpy@plt>
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:232
  14d84e:	48 8b 44 24 10       	mov    0x10(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14d853:	48 89 84 24 48 01 00 	mov    %rax,0x148(%rsp)
  14d85a:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d85b:	48 8b 8c 24 40 01 00 	mov    0x140(%rsp),%rcx
  14d862:	00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14d863:	c6 04 01 00          	movb   $0x0,(%rcx,%rax,1)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14d867:	48 8d 44 24 20       	lea    0x20(%rsp),%rax
  14d86c:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d871:	4d 8b 7e 40          	mov    0x40(%r14),%r15
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14d875:	49 8b 5e 48          	mov    0x48(%r14),%rbx
bool __gnu_cxx::__is_null_pointer<char>(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/type_traits.h:153
  14d879:	4d 85 ff             	test   %r15,%r15
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:211
  14d87c:	75 09                	jne    14d887 <MultiSteersOdometer::CalSpeed()+0x1f7>
  14d87e:	48 85 db             	test   %rbx,%rbx
  14d881:	0f 85 49 14 00 00    	jne    14ecd0 <MultiSteersOdometer::CalSpeed()+0x1640>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:215
  14d887:	48 89 9c 24 b0 00 00 	mov    %rbx,0xb0(%rsp)
  14d88e:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d88f:	48 8d 44 24 20       	lea    0x20(%rsp),%rax
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:217
  14d894:	48 83 fb 10          	cmp    $0x10,%rbx
  14d898:	72 26                	jb     14d8c0 <MultiSteersOdometer::CalSpeed()+0x230>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:219
  14d89a:	31 d2                	xor    %edx,%edx
  14d89c:	48 8d 7c 24 10       	lea    0x10(%rsp),%rdi
  14d8a1:	48 8d b4 24 b0 00 00 	lea    0xb0(%rsp),%rsi
  14d8a8:	00 
  14d8a9:	e8 82 78 f3 ff       	call   85130 <std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_create(unsigned long&, unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14d8ae:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:220
  14d8b3:	48 8b 8c 24 b0 00 00 	mov    0xb0(%rsp),%rcx
  14d8ba:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14d8bb:	48 89 4c 24 20       	mov    %rcx,0x20(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  14d8c0:	48 85 db             	test   %rbx,%rbx
  14d8c3:	74 29                	je     14d8ee <MultiSteersOdometer::CalSpeed()+0x25e>
  14d8c5:	48 83 fb 01          	cmp    $0x1,%rbx
  14d8c9:	75 15                	jne    14d8e0 <MultiSteersOdometer::CalSpeed()+0x250>
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14d8cb:	41 0f b6 0f          	movzbl (%r15),%ecx
  14d8cf:	88 08                	mov    %cl,(%rax)
  14d8d1:	eb 1b                	jmp    14d8ee <MultiSteersOdometer::CalSpeed()+0x25e>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14d8d3:	66 66 66 66 2e 0f 1f 	data16 data16 data16 cs nopw 0x0(%rax,%rax,1)
  14d8da:	84 00 00 00 00 00 
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14d8e0:	48 89 c7             	mov    %rax,%rdi
  14d8e3:	4c 89 fe             	mov    %r15,%rsi
  14d8e6:	48 89 da             	mov    %rbx,%rdx
  14d8e9:	e8 82 5b f3 ff       	call   83470 <memcpy@plt>
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:232
  14d8ee:	48 8b 84 24 b0 00 00 	mov    0xb0(%rsp),%rax
  14d8f5:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14d8f6:	48 89 44 24 18       	mov    %rax,0x18(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d8fb:	48 8b 4c 24 10       	mov    0x10(%rsp),%rcx
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14d900:	c6 04 01 00          	movb   $0x0,(%rcx,%rax,1)
  14d904:	4c 8b bc 24 e8 00 00 	mov    0xe8(%rsp),%r15
  14d90b:	00 
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:122
  14d90c:	4c 89 ff             	mov    %r15,%rdi
  14d90f:	48 8d b4 24 40 01 00 	lea    0x140(%rsp),%rsi
  14d916:	00 
  14d917:	e8 04 61 f3 ff       	call   83a20 <std::map<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, MotorVitalInfo, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, MotorVitalInfo> > >::operator[](std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&)@plt>
  14d91c:	f2 0f 10 40 30       	movsd  0x30(%rax),%xmm0
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:123
  14d921:	f2 0f 11 44 24 08    	movsd  %xmm0,0x8(%rsp)
  14d927:	4c 89 ff             	mov    %r15,%rdi
  14d92a:	48 8d 74 24 10       	lea    0x10(%rsp),%rsi
  14d92f:	e8 ec 60 f3 ff       	call   83a20 <std::map<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, MotorVitalInfo, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, MotorVitalInfo> > >::operator[](std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&)@plt>
  14d934:	f2 0f 10 40 20       	movsd  0x20(%rax),%xmm0
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:124
  14d939:	f2 0f 11 84 24 90 00 	movsd  %xmm0,0x90(%rsp)
  14d940:	00 00 
  14d942:	e8 d9 85 f3 ff       	call   85f20 <cos@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:564
  14d947:	48 8b 44 24 70       	mov    0x70(%rsp),%rax
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:124
  14d94c:	f2 0f 59 44 24 08    	mulsd  0x8(%rsp),%xmm0
  14d952:	48 8b 9c 24 98 00 00 	mov    0x98(%rsp),%rbx
  14d959:	00 
  14d95a:	f2 0f 11 04 18       	movsd  %xmm0,(%rax,%rbx,1)
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:125
  14d95f:	f2 0f 10 84 24 90 00 	movsd  0x90(%rsp),%xmm0
  14d966:	00 00 
  14d968:	e8 93 67 f3 ff       	call   84100 <sin@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:564
  14d96d:	48 8b 44 24 70       	mov    0x70(%rsp),%rax
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:125
  14d972:	f2 0f 59 44 24 08    	mulsd  0x8(%rsp),%xmm0
  14d978:	f2 0f 11 44 18 08    	movsd  %xmm0,0x8(%rax,%rbx,1)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d97e:	48 8b 7c 24 10       	mov    0x10(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d983:	48 8d 44 24 20       	lea    0x20(%rsp),%rax
  14d988:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d98b:	74 05                	je     14d992 <MultiSteersOdometer::CalSpeed()+0x302>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d98d:	e8 9e 70 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d992:	48 8b bc 24 40 01 00 	mov    0x140(%rsp),%rdi
  14d999:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d99a:	4c 39 e7             	cmp    %r12,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d99d:	74 05                	je     14d9a4 <MultiSteersOdometer::CalSpeed()+0x314>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d99f:	e8 8c 70 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >::operator++(int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:295
  14d9a4:	4c 89 f7             	mov    %r14,%rdi
  14d9a7:	e8 74 87 f3 ff       	call   86120 <std::_Rb_tree_increment(std::_Rb_tree_node_base*)@plt>
  14d9ac:	49 89 c6             	mov    %rax,%r14
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:119
  14d9af:	48 83 c3 10          	add    $0x10,%rbx
std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >::operator!=(std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:320
  14d9b3:	4c 3b b4 24 88 00 00 	cmp    0x88(%rsp),%r14
  14d9ba:	00 
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:119
  14d9bb:	0f 85 0f fe ff ff    	jne    14d7d0 <MultiSteersOdometer::CalSpeed()+0x140>
Eigen::internal::assign_op<double, double>::assignCoeff(double&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/AssignmentFunctors.h:24
  14d9c1:	66 0f 57 c0          	xorpd  %xmm0,%xmm0
  14d9c5:	66 0f 29 84 24 d0 00 	movapd %xmm0,0xd0(%rsp)
  14d9cc:	00 00 
  14d9ce:	48 c7 84 24 e0 00 00 	movq   $0x0,0xe0(%rsp)
  14d9d5:	00 00 00 00 00 
  14d9da:	4c 8b 64 24 38       	mov    0x38(%rsp),%r12
Eigen::DenseStorage<double, -1, -1, -1, 0>::rows() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:394
  14d9df:	49 8b bc 24 98 01 00 	mov    0x198(%r12),%rdi
  14d9e6:	00 
Eigen::DenseStorage<double, -1, -1, -1, 0>::cols() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:395
  14d9e7:	49 8b b4 24 a0 01 00 	mov    0x1a0(%r12),%rsi
  14d9ee:	00 
Eigen::DenseStorage<double, -1, -1, -1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:416
  14d9ef:	49 8b 84 24 90 01 00 	mov    0x190(%r12),%rax
  14d9f6:	00 
Eigen::internal::blas_data_mapper<double const, long, 0, 0, 1>::blas_data_mapper(double const*, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/BlasUtil.h:213
  14d9f7:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  14d9fe:	00 
  14d9ff:	48 89 bc 24 48 01 00 	mov    %rdi,0x148(%rsp)
  14da06:	00 
Eigen::DenseStorage<double, -1, -1, 1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:564
  14da07:	48 8b 44 24 70       	mov    0x70(%rsp),%rax
Eigen::internal::blas_data_mapper<double const, long, 1, 0, 1>::blas_data_mapper(double const*, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/BlasUtil.h:213
  14da0c:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
  14da11:	48 c7 44 24 18 01 00 	movq   $0x1,0x18(%rsp)
  14da18:	00 00 
  14da1a:	48 8d 94 24 40 01 00 	lea    0x140(%rsp),%rdx
  14da21:	00 
MultiSteersOdometer::CalSpeed():
  14da22:	48 8d 4c 24 10       	lea    0x10(%rsp),%rcx
  14da27:	4c 8d 84 24 d0 00 00 	lea    0xd0(%rsp),%r8
  14da2e:	00 
void Eigen::internal::gemv_dense_selector<2, 0, true>::run<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, -1, 1, 0, -1, 1>, Eigen::Matrix<double, 3, 1, 0, 3, 1> >(Eigen::Matrix<double, -1, -1, 0, -1, -1> const&, Eigen::Matrix<double, -1, 1, 0, -1, 1> const&, Eigen::Matrix<double, 3, 1, 0, 3, 1>&, Eigen::Matrix<double, 3, 1, 0, 3, 1>::Scalar const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/GeneralProduct.h:243
  14da2f:	f2 0f 10 05 41 ae 03 	movsd  0x3ae41(%rip),%xmm0        # 188878 <_fini+0x84>
  14da36:	00 
  14da37:	41 b9 01 00 00 00    	mov    $0x1,%r9d
  14da3d:	e8 2e 84 f3 ff       	call   85e70 <Eigen::internal::general_matrix_vector_product<long, double, Eigen::internal::const_blas_data_mapper<double, long, 0>, 0, false, double, Eigen::internal::const_blas_data_mapper<double, long, 1>, false, 0>::run(long, long, Eigen::internal::const_blas_data_mapper<double, long, 0> const&, Eigen::internal::const_blas_data_mapper<double, long, 1> const&, double*, long, double)@plt>
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:131
  14da42:	66 0f 28 84 24 d0 00 	movapd 0xd0(%rsp),%xmm0
  14da49:	00 00 
  14da4b:	66 41 0f 11 84 24 d8 	movupd %xmm0,0xd8(%r12)
  14da52:	00 00 00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:133
  14da55:	48 8b 84 24 e0 00 00 	mov    0xe0(%rsp),%rax
  14da5c:	00 
  14da5d:	49 89 84 24 e8 00 00 	mov    %rax,0xe8(%r12)
  14da64:	00 
Eigen::DenseStorage<double, -1, -1, 1, 0>::DenseStorage():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:500
  14da65:	66 0f 57 c0          	xorpd  %xmm0,%xmm0
  14da69:	66 0f 29 84 24 a0 00 	movapd %xmm0,0xa0(%rsp)
  14da70:	00 00 
Eigen::DenseStorage<double, -1, -1, -1, 0>::rows() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:394
  14da72:	49 8b b4 24 80 01 00 	mov    0x180(%r12),%rsi
  14da79:	00 
MultiSteersOdometer::CalSpeed():
  14da7a:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  14da81:	00 
void Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> >::resizeLike<Eigen::CwiseBinaryOp<Eigen::internal::scalar_difference_op<double, double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> const, Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 0> const> >(Eigen::EigenBase<Eigen::CwiseBinaryOp<Eigen::internal::scalar_difference_op<double, double>, Eigen::Matrix<double, -1, 1, 0, -1, 1> const, Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 0> const> > const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/PlainObjectBase.h:375
  14da82:	ba 01 00 00 00       	mov    $0x1,%edx
  14da87:	e8 d4 70 f3 ff       	call   84b60 <Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> >::resize(long, long)@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:564
  14da8c:	4c 8b 7c 24 70       	mov    0x70(%rsp),%r15
Eigen::DenseStorage<double, -1, -1, 1, 0>::rows() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:544
  14da91:	48 8b 74 24 78       	mov    0x78(%rsp),%rsi
void Eigen::internal::resize_if_allowed<Eigen::Matrix<double, -1, 1, 0, -1, 1>, Eigen::Matrix<double, -1, 1, 0, -1, 1>, double, double>(Eigen::Matrix<double, -1, 1, 0, -1, 1>&, Eigen::Matrix<double, -1, 1, 0, -1, 1> const&, Eigen::internal::assign_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:719
  14da96:	48 39 b4 24 a8 00 00 	cmp    %rsi,0xa8(%rsp)
  14da9d:	00 
  14da9e:	74 1a                	je     14daba <MultiSteersOdometer::CalSpeed()+0x42a>
MultiSteersOdometer::CalSpeed():
  14daa0:	48 8d bc 24 a0 00 00 	lea    0xa0(%rsp),%rdi
  14daa7:	00 
void Eigen::internal::resize_if_allowed<Eigen::Matrix<double, -1, 1, 0, -1, 1>, Eigen::Matrix<double, -1, 1, 0, -1, 1>, double, double>(Eigen::Matrix<double, -1, 1, 0, -1, 1>&, Eigen::Matrix<double, -1, 1, 0, -1, 1> const&, Eigen::internal::assign_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:720
  14daa8:	ba 01 00 00 00       	mov    $0x1,%edx
  14daad:	e8 ae 70 f3 ff       	call   84b60 <Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> >::resize(long, long)@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::rows() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:544
  14dab2:	48 8b b4 24 a8 00 00 	mov    0xa8(%rsp),%rsi
  14dab9:	00 
Eigen::DenseStorage<double, -1, -1, 1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:564
  14daba:	48 8b 84 24 a0 00 00 	mov    0xa0(%rsp),%rax
  14dac1:	00 
Eigen::internal::dense_assignment_loop<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>, 3, 0>::run(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:411
  14dac2:	49 89 f2             	mov    %rsi,%r10
  14dac5:	49 c1 ea 3f          	shr    $0x3f,%r10
  14dac9:	49 01 f2             	add    %rsi,%r10
  14dacc:	4c 89 d1             	mov    %r10,%rcx
  14dacf:	48 83 e1 fe          	and    $0xfffffffffffffffe,%rcx
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14dad3:	48 83 fe 02          	cmp    $0x2,%rsi
  14dad7:	0f 8c e8 00 00 00    	jl     14dbc5 <MultiSteersOdometer::CalSpeed()+0x535>
  14dadd:	48 83 f9 01          	cmp    $0x1,%rcx
  14dae1:	ba 02 00 00 00       	mov    $0x2,%edx
  14dae6:	48 0f 4f d1          	cmovg  %rcx,%rdx
  14daea:	48 83 c2 ff          	add    $0xffffffffffffffff,%rdx
  14daee:	49 89 d0             	mov    %rdx,%r8
  14daf1:	49 d1 e8             	shr    %r8
  14daf4:	41 8d 78 01          	lea    0x1(%r8),%edi
  14daf8:	83 e7 07             	and    $0x7,%edi
  14dafb:	48 83 fa 0e          	cmp    $0xe,%rdx
  14daff:	73 33                	jae    14db34 <MultiSteersOdometer::CalSpeed()+0x4a4>
MultiSteersOdometer::CalSpeed():
  14db01:	31 d2                	xor    %edx,%edx
Eigen::internal::dense_assignment_loop<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>, 3, 0>::run(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14db03:	48 85 ff             	test   %rdi,%rdi
  14db06:	0f 85 9b 00 00 00    	jne    14dba7 <MultiSteersOdometer::CalSpeed()+0x517>
  14db0c:	e9 b4 00 00 00       	jmp    14dbc5 <MultiSteersOdometer::CalSpeed()+0x535>
MultiSteersOdometer::CalSpeed():
  14db11:	31 c0                	xor    %eax,%eax
  14db13:	e9 29 11 00 00       	jmp    14ec41 <MultiSteersOdometer::CalSpeed()+0x15b1>
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:151
  14db18:	66 0f 57 c0          	xorpd  %xmm0,%xmm0
  14db1c:	66 0f 11 83 d8 00 00 	movupd %xmm0,0xd8(%rbx)
  14db23:	00 
  14db24:	48 c7 83 e8 00 00 00 	movq   $0x0,0xe8(%rbx)
  14db2b:	00 00 00 00 
  14db2f:	e9 0b 11 00 00       	jmp    14ec3f <MultiSteersOdometer::CalSpeed()+0x15af>
Eigen::internal::dense_assignment_loop<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>, 3, 0>::run(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14db34:	48 8d 5f ff          	lea    -0x1(%rdi),%rbx
  14db38:	4c 29 c3             	sub    %r8,%rbx
  14db3b:	31 d2                	xor    %edx,%edx
double __vector(2) Eigen::internal::pload<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14db3d:	0f 1f 00             	nopl   (%rax)
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:307
  14db40:	41 0f 28 04 d7       	movaps (%r15,%rdx,8),%xmm0
void Eigen::internal::pstore<double, double __vector(2)>(double*, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:359
  14db45:	0f 29 04 d0          	movaps %xmm0,(%rax,%rdx,8)
double __vector(2) Eigen::internal::pload<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:307
  14db49:	41 0f 28 44 d7 10    	movaps 0x10(%r15,%rdx,8),%xmm0
void Eigen::internal::pstore<double, double __vector(2)>(double*, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:359
  14db4f:	0f 29 44 d0 10       	movaps %xmm0,0x10(%rax,%rdx,8)
double __vector(2) Eigen::internal::pload<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:307
  14db54:	41 0f 28 44 d7 20    	movaps 0x20(%r15,%rdx,8),%xmm0
void Eigen::internal::pstore<double, double __vector(2)>(double*, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:359
  14db5a:	0f 29 44 d0 20       	movaps %xmm0,0x20(%rax,%rdx,8)
double __vector(2) Eigen::internal::pload<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:307
  14db5f:	41 0f 28 44 d7 30    	movaps 0x30(%r15,%rdx,8),%xmm0
void Eigen::internal::pstore<double, double __vector(2)>(double*, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:359
  14db65:	0f 29 44 d0 30       	movaps %xmm0,0x30(%rax,%rdx,8)
double __vector(2) Eigen::internal::pload<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:307
  14db6a:	41 0f 28 44 d7 40    	movaps 0x40(%r15,%rdx,8),%xmm0
void Eigen::internal::pstore<double, double __vector(2)>(double*, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:359
  14db70:	0f 29 44 d0 40       	movaps %xmm0,0x40(%rax,%rdx,8)
double __vector(2) Eigen::internal::pload<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:307
  14db75:	41 0f 28 44 d7 50    	movaps 0x50(%r15,%rdx,8),%xmm0
void Eigen::internal::pstore<double, double __vector(2)>(double*, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:359
  14db7b:	0f 29 44 d0 50       	movaps %xmm0,0x50(%rax,%rdx,8)
double __vector(2) Eigen::internal::pload<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:307
  14db80:	41 0f 28 44 d7 60    	movaps 0x60(%r15,%rdx,8),%xmm0
void Eigen::internal::pstore<double, double __vector(2)>(double*, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:359
  14db86:	0f 29 44 d0 60       	movaps %xmm0,0x60(%rax,%rdx,8)
double __vector(2) Eigen::internal::pload<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:307
  14db8b:	66 41 0f 28 44 d7 70 	movapd 0x70(%r15,%rdx,8),%xmm0
void Eigen::internal::pstore<double, double __vector(2)>(double*, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:359
  14db92:	66 0f 29 44 d0 70    	movapd %xmm0,0x70(%rax,%rdx,8)
Eigen::internal::dense_assignment_loop<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>, 3, 0>::run(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14db98:	48 83 c2 10          	add    $0x10,%rdx
  14db9c:	48 83 c3 08          	add    $0x8,%rbx
  14dba0:	75 9e                	jne    14db40 <MultiSteersOdometer::CalSpeed()+0x4b0>
  14dba2:	48 85 ff             	test   %rdi,%rdi
  14dba5:	74 1e                	je     14dbc5 <MultiSteersOdometer::CalSpeed()+0x535>
  14dba7:	48 c1 e2 03          	shl    $0x3,%rdx
  14dbab:	48 f7 df             	neg    %rdi
double __vector(2) Eigen::internal::pload<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14dbae:	66 90                	xchg   %ax,%ax
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:307
  14dbb0:	66 41 0f 28 04 17    	movapd (%r15,%rdx,1),%xmm0
void Eigen::internal::pstore<double, double __vector(2)>(double*, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:359
  14dbb6:	66 0f 29 04 10       	movapd %xmm0,(%rax,%rdx,1)
Eigen::internal::dense_assignment_loop<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>, 3, 0>::run(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14dbbb:	48 83 c2 10          	add    $0x10,%rdx
  14dbbf:	48 83 c7 01          	add    $0x1,%rdi
  14dbc3:	75 eb                	jne    14dbb0 <MultiSteersOdometer::CalSpeed()+0x520>
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14dbc5:	49 89 f1             	mov    %rsi,%r9
  14dbc8:	49 29 c9             	sub    %rcx,%r9
  14dbcb:	0f 8e c6 01 00 00    	jle    14dd97 <MultiSteersOdometer::CalSpeed()+0x707>
  14dbd1:	49 83 f9 04          	cmp    $0x4,%r9
  14dbd5:	0f 82 23 01 00 00    	jb     14dcfe <MultiSteersOdometer::CalSpeed()+0x66e>
  14dbdb:	48 8d 14 c8          	lea    (%rax,%rcx,8),%rdx
  14dbdf:	49 8d 3c f7          	lea    (%r15,%rsi,8),%rdi
  14dbe3:	48 39 fa             	cmp    %rdi,%rdx
  14dbe6:	73 11                	jae    14dbf9 <MultiSteersOdometer::CalSpeed()+0x569>
  14dbe8:	48 8d 14 f0          	lea    (%rax,%rsi,8),%rdx
  14dbec:	49 8d 3c cf          	lea    (%r15,%rcx,8),%rdi
  14dbf0:	48 39 d7             	cmp    %rdx,%rdi
  14dbf3:	0f 82 05 01 00 00    	jb     14dcfe <MultiSteersOdometer::CalSpeed()+0x66e>
  14dbf9:	4d 89 c8             	mov    %r9,%r8
  14dbfc:	49 83 e0 fc          	and    $0xfffffffffffffffc,%r8
  14dc00:	49 8d 78 fc          	lea    -0x4(%r8),%rdi
  14dc04:	48 89 fa             	mov    %rdi,%rdx
  14dc07:	48 c1 ea 02          	shr    $0x2,%rdx
  14dc0b:	44 8d 5a 01          	lea    0x1(%rdx),%r11d
  14dc0f:	41 83 e3 03          	and    $0x3,%r11d
  14dc13:	48 83 ff 0c          	cmp    $0xc,%rdi
  14dc17:	73 10                	jae    14dc29 <MultiSteersOdometer::CalSpeed()+0x599>
MultiSteersOdometer::CalSpeed():
  14dc19:	31 d2                	xor    %edx,%edx
  14dc1b:	4d 85 db             	test   %r11,%r11
  14dc1e:	0f 85 95 00 00 00    	jne    14dcb9 <MultiSteersOdometer::CalSpeed()+0x629>
  14dc24:	e9 c9 00 00 00       	jmp    14dcf2 <MultiSteersOdometer::CalSpeed()+0x662>
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14dc29:	4d 8d 34 cf          	lea    (%r15,%rcx,8),%r14
  14dc2d:	49 83 c6 70          	add    $0x70,%r14
  14dc31:	48 8d 3c c8          	lea    (%rax,%rcx,8),%rdi
  14dc35:	48 83 c7 70          	add    $0x70,%rdi
  14dc39:	49 8d 5b ff          	lea    -0x1(%r11),%rbx
  14dc3d:	48 29 d3             	sub    %rdx,%rbx
  14dc40:	31 d2                	xor    %edx,%edx
Eigen::internal::assign_op<double, double>::assignCoeff(double&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14dc42:	66 66 66 66 66 2e 0f 	data16 data16 data16 data16 cs nopw 0x0(%rax,%rax,1)
  14dc49:	1f 84 00 00 00 00 00 
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/AssignmentFunctors.h:24
  14dc50:	41 0f 10 44 d6 90    	movups -0x70(%r14,%rdx,8),%xmm0
  14dc56:	41 0f 10 4c d6 a0    	movups -0x60(%r14,%rdx,8),%xmm1
  14dc5c:	0f 11 44 d7 90       	movups %xmm0,-0x70(%rdi,%rdx,8)
  14dc61:	0f 11 4c d7 a0       	movups %xmm1,-0x60(%rdi,%rdx,8)
  14dc66:	41 0f 10 44 d6 b0    	movups -0x50(%r14,%rdx,8),%xmm0
  14dc6c:	41 0f 10 4c d6 c0    	movups -0x40(%r14,%rdx,8),%xmm1
  14dc72:	0f 11 44 d7 b0       	movups %xmm0,-0x50(%rdi,%rdx,8)
  14dc77:	0f 11 4c d7 c0       	movups %xmm1,-0x40(%rdi,%rdx,8)
  14dc7c:	41 0f 10 44 d6 d0    	movups -0x30(%r14,%rdx,8),%xmm0
  14dc82:	41 0f 10 4c d6 e0    	movups -0x20(%r14,%rdx,8),%xmm1
  14dc88:	0f 11 44 d7 d0       	movups %xmm0,-0x30(%rdi,%rdx,8)
  14dc8d:	0f 11 4c d7 e0       	movups %xmm1,-0x20(%rdi,%rdx,8)
  14dc92:	66 41 0f 10 44 d6 f0 	movupd -0x10(%r14,%rdx,8),%xmm0
  14dc99:	66 41 0f 10 0c d6    	movupd (%r14,%rdx,8),%xmm1
  14dc9f:	66 0f 11 44 d7 f0    	movupd %xmm0,-0x10(%rdi,%rdx,8)
  14dca5:	66 0f 11 0c d7       	movupd %xmm1,(%rdi,%rdx,8)
  14dcaa:	48 83 c2 10          	add    $0x10,%rdx
  14dcae:	48 83 c3 04          	add    $0x4,%rbx
  14dcb2:	75 9c                	jne    14dc50 <MultiSteersOdometer::CalSpeed()+0x5c0>
MultiSteersOdometer::CalSpeed():
  14dcb4:	4d 85 db             	test   %r11,%r11
  14dcb7:	74 39                	je     14dcf2 <MultiSteersOdometer::CalSpeed()+0x662>
  14dcb9:	49 d1 fa             	sar    %r10
  14dcbc:	49 c1 e2 04          	shl    $0x4,%r10
  14dcc0:	49 8d 14 d2          	lea    (%r10,%rdx,8),%rdx
  14dcc4:	48 83 c2 10          	add    $0x10,%rdx
  14dcc8:	49 f7 db             	neg    %r11
  14dccb:	0f 1f 44 00 00       	nopl   0x0(%rax,%rax,1)
Eigen::internal::assign_op<double, double>::assignCoeff(double&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/AssignmentFunctors.h:24
  14dcd0:	66 41 0f 10 44 17 f0 	movupd -0x10(%r15,%rdx,1),%xmm0
  14dcd7:	66 41 0f 10 0c 17    	movupd (%r15,%rdx,1),%xmm1
  14dcdd:	66 0f 11 44 10 f0    	movupd %xmm0,-0x10(%rax,%rdx,1)
  14dce3:	66 0f 11 0c 10       	movupd %xmm1,(%rax,%rdx,1)
  14dce8:	48 83 c2 20          	add    $0x20,%rdx
  14dcec:	49 83 c3 01          	add    $0x1,%r11
  14dcf0:	75 de                	jne    14dcd0 <MultiSteersOdometer::CalSpeed()+0x640>
MultiSteersOdometer::CalSpeed():
  14dcf2:	4d 39 c1             	cmp    %r8,%r9
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14dcf5:	0f 84 9c 00 00 00    	je     14dd97 <MultiSteersOdometer::CalSpeed()+0x707>
MultiSteersOdometer::CalSpeed():
  14dcfb:	4c 01 c1             	add    %r8,%rcx
Eigen::internal::evaluator<Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> > >::coeffRef(long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:187
  14dcfe:	89 f7                	mov    %esi,%edi
  14dd00:	29 cf                	sub    %ecx,%edi
  14dd02:	48 8d 56 ff          	lea    -0x1(%rsi),%rdx
  14dd06:	48 29 ca             	sub    %rcx,%rdx
  14dd09:	48 83 e7 07          	and    $0x7,%rdi
  14dd0d:	74 23                	je     14dd32 <MultiSteersOdometer::CalSpeed()+0x6a2>
  14dd0f:	48 f7 df             	neg    %rdi
Eigen::internal::assign_op<double, double>::assignCoeff(double&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:187
  14dd12:	66 66 66 66 66 2e 0f 	data16 data16 data16 data16 cs nopw 0x0(%rax,%rax,1)
  14dd19:	1f 84 00 00 00 00 00 
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/AssignmentFunctors.h:24
  14dd20:	49 8b 1c cf          	mov    (%r15,%rcx,8),%rbx
  14dd24:	48 89 1c c8          	mov    %rbx,(%rax,%rcx,8)
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14dd28:	48 83 c1 01          	add    $0x1,%rcx
  14dd2c:	48 83 c7 01          	add    $0x1,%rdi
  14dd30:	75 ee                	jne    14dd20 <MultiSteersOdometer::CalSpeed()+0x690>
Eigen::internal::evaluator<Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> > >::coeffRef(long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:187
  14dd32:	48 83 fa 07          	cmp    $0x7,%rdx
  14dd36:	72 5f                	jb     14dd97 <MultiSteersOdometer::CalSpeed()+0x707>
Eigen::internal::assign_op<double, double>::assignCoeff(double&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:187
  14dd38:	0f 1f 84 00 00 00 00 	nopl   0x0(%rax,%rax,1)
  14dd3f:	00 
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/AssignmentFunctors.h:24
  14dd40:	49 8b 14 cf          	mov    (%r15,%rcx,8),%rdx
  14dd44:	48 89 14 c8          	mov    %rdx,(%rax,%rcx,8)
  14dd48:	49 8b 54 cf 08       	mov    0x8(%r15,%rcx,8),%rdx
  14dd4d:	48 89 54 c8 08       	mov    %rdx,0x8(%rax,%rcx,8)
  14dd52:	49 8b 54 cf 10       	mov    0x10(%r15,%rcx,8),%rdx
  14dd57:	48 89 54 c8 10       	mov    %rdx,0x10(%rax,%rcx,8)
  14dd5c:	49 8b 54 cf 18       	mov    0x18(%r15,%rcx,8),%rdx
  14dd61:	48 89 54 c8 18       	mov    %rdx,0x18(%rax,%rcx,8)
  14dd66:	49 8b 54 cf 20       	mov    0x20(%r15,%rcx,8),%rdx
  14dd6b:	48 89 54 c8 20       	mov    %rdx,0x20(%rax,%rcx,8)
  14dd70:	49 8b 54 cf 28       	mov    0x28(%r15,%rcx,8),%rdx
  14dd75:	48 89 54 c8 28       	mov    %rdx,0x28(%rax,%rcx,8)
  14dd7a:	49 8b 54 cf 30       	mov    0x30(%r15,%rcx,8),%rdx
  14dd7f:	48 89 54 c8 30       	mov    %rdx,0x30(%rax,%rcx,8)
  14dd84:	49 8b 54 cf 38       	mov    0x38(%r15,%rcx,8),%rdx
  14dd89:	48 89 54 c8 38       	mov    %rdx,0x38(%rax,%rcx,8)
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14dd8e:	48 83 c1 08          	add    $0x8,%rcx
  14dd92:	48 39 ce             	cmp    %rcx,%rsi
  14dd95:	75 a9                	jne    14dd40 <MultiSteersOdometer::CalSpeed()+0x6b0>
Eigen::DenseStorage<double, -1, -1, 1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:564
  14dd97:	48 8b 84 24 a0 00 00 	mov    0xa0(%rsp),%rax
  14dd9e:	00 
Eigen::DenseStorage<double, -1, -1, 1, 0>::rows() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:544
  14dd9f:	4c 8b b4 24 a8 00 00 	mov    0xa8(%rsp),%r14
  14dda6:	00 
Eigen::internal::dense_assignment_loop<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0>, 3, 0>::run(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0>&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:411
  14dda7:	4c 89 f2             	mov    %r14,%rdx
  14ddaa:	48 c1 ea 3f          	shr    $0x3f,%rdx
  14ddae:	4c 01 f2             	add    %r14,%rdx
  14ddb1:	48 83 e2 fe          	and    $0xfffffffffffffffe,%rdx
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14ddb5:	49 83 fe 02          	cmp    $0x2,%r14
  14ddb9:	0f 8c 82 00 00 00    	jl     14de41 <MultiSteersOdometer::CalSpeed()+0x7b1>
MultiSteersOdometer::CalSpeed():
  14ddbf:	49 8b b4 24 78 01 00 	mov    0x178(%r12),%rsi
  14ddc6:	00 
  14ddc7:	49 8b bc 24 80 01 00 	mov    0x180(%r12),%rdi
  14ddce:	00 
Eigen::internal::dense_assignment_loop<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0>, 3, 0>::run(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0>&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14ddcf:	48 8d 1c fe          	lea    (%rsi,%rdi,8),%rbx
  14ddd3:	48 c1 e7 04          	shl    $0x4,%rdi
  14ddd7:	48 01 f7             	add    %rsi,%rdi
  14ddda:	31 c9                	xor    %ecx,%ecx
double __vector(2) Eigen::internal::ploadu<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14dddc:	0f 1f 40 00          	nopl   0x0(%rax)
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:336
  14dde0:	66 0f 10 04 ce       	movupd (%rsi,%rcx,8),%xmm0
double __vector(2) Eigen::internal::pset1<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:179
  14dde5:	f2 0f 10 8c 24 d0 00 	movsd  0xd0(%rsp),%xmm1
  14ddec:	00 00 
  14ddee:	f2 0f 10 94 24 d8 00 	movsd  0xd8(%rsp),%xmm2
  14ddf5:	00 00 
  14ddf7:	66 0f 14 c9          	unpcklpd %xmm1,%xmm1
double __vector(2) Eigen::internal::pmul<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:226
  14ddfb:	66 0f 59 c8          	mulpd  %xmm0,%xmm1
double __vector(2) Eigen::internal::ploadu<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:336
  14ddff:	66 0f 10 04 cb       	movupd (%rbx,%rcx,8),%xmm0
double __vector(2) Eigen::internal::pset1<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:179
  14de04:	66 0f 14 d2          	unpcklpd %xmm2,%xmm2
double __vector(2) Eigen::internal::pmul<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:226
  14de08:	66 0f 59 d0          	mulpd  %xmm0,%xmm2
double __vector(2) Eigen::internal::padd<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:199
  14de0c:	66 0f 58 d1          	addpd  %xmm1,%xmm2
double __vector(2) Eigen::internal::ploadu<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:336
  14de10:	66 0f 10 04 cf       	movupd (%rdi,%rcx,8),%xmm0
double __vector(2) Eigen::internal::pset1<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:179
  14de15:	f2 0f 10 8c 24 e0 00 	movsd  0xe0(%rsp),%xmm1
  14de1c:	00 00 
  14de1e:	66 0f 14 c9          	unpcklpd %xmm1,%xmm1
double __vector(2) Eigen::internal::pmul<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:226
  14de22:	66 0f 59 c8          	mulpd  %xmm0,%xmm1
double __vector(2) Eigen::internal::padd<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:199
  14de26:	66 0f 58 ca          	addpd  %xmm2,%xmm1
double __vector(2) Eigen::internal::pload<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:307
  14de2a:	66 0f 28 04 c8       	movapd (%rax,%rcx,8),%xmm0
double __vector(2) Eigen::internal::psub<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:203
  14de2f:	66 0f 5c c1          	subpd  %xmm1,%xmm0
void Eigen::internal::pstore<double, double __vector(2)>(double*, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:359
  14de33:	66 0f 29 04 c8       	movapd %xmm0,(%rax,%rcx,8)
Eigen::internal::dense_assignment_loop<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0>, 3, 0>::run(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0>&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14de38:	48 83 c1 02          	add    $0x2,%rcx
  14de3c:	48 39 d1             	cmp    %rdx,%rcx
  14de3f:	7c 9f                	jl     14dde0 <MultiSteersOdometer::CalSpeed()+0x750>
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14de41:	4d 89 f1             	mov    %r14,%r9
  14de44:	49 29 d1             	sub    %rdx,%r9
  14de47:	0f 8e cc 01 00 00    	jle    14e019 <MultiSteersOdometer::CalSpeed()+0x989>
MultiSteersOdometer::CalSpeed():
  14de4d:	49 8b b4 24 78 01 00 	mov    0x178(%r12),%rsi
  14de54:	00 
  14de55:	4d 8b 94 24 80 01 00 	mov    0x180(%r12),%r10
  14de5c:	00 
  14de5d:	4b 8d 0c 12          	lea    (%r10,%r10,1),%rcx
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14de61:	49 83 f9 02          	cmp    $0x2,%r9
  14de65:	0f 82 54 01 00 00    	jb     14dfbf <MultiSteersOdometer::CalSpeed()+0x92f>
  14de6b:	48 8d 1c d0          	lea    (%rax,%rdx,8),%rbx
  14de6f:	4e 8d 3c f0          	lea    (%rax,%r14,8),%r15
  14de73:	48 8d 3c 11          	lea    (%rcx,%rdx,1),%rdi
  14de77:	4c 8d 04 fe          	lea    (%rsi,%rdi,8),%r8
  14de7b:	48 89 4c 24 08       	mov    %rcx,0x8(%rsp)
  14de80:	49 8d 3c 0e          	lea    (%r14,%rcx,1),%rdi
  14de84:	4c 8d 1c fe          	lea    (%rsi,%rdi,8),%r11
  14de88:	49 8d 3c 12          	lea    (%r10,%rdx,1),%rdi
  14de8c:	48 8d 0c fe          	lea    (%rsi,%rdi,8),%rcx
  14de90:	4b 8d 3c 32          	lea    (%r10,%r14,1),%rdi
  14de94:	4c 8d 24 fe          	lea    (%rsi,%rdi,8),%r12
  14de98:	48 8d 3c d6          	lea    (%rsi,%rdx,8),%rdi
  14de9c:	4c 39 db             	cmp    %r11,%rbx
  14de9f:	4e 8d 1c f6          	lea    (%rsi,%r14,8),%r11
  14dea3:	0f 92 84 24 98 00 00 	setb   0x98(%rsp)
  14deaa:	00 
  14deab:	4d 39 f8             	cmp    %r15,%r8
  14deae:	41 0f 92 c5          	setb   %r13b
  14deb2:	4c 39 e3             	cmp    %r12,%rbx
  14deb5:	4c 8d a4 24 e1 00 00 	lea    0xe1(%rsp),%r12
  14debc:	00 
  14debd:	41 0f 92 c0          	setb   %r8b
  14dec1:	4c 39 f9             	cmp    %r15,%rcx
  14dec4:	0f 92 84 24 90 00 00 	setb   0x90(%rsp)
  14decb:	00 
  14decc:	4c 39 db             	cmp    %r11,%rbx
  14decf:	41 0f 92 c3          	setb   %r11b
  14ded3:	4c 39 ff             	cmp    %r15,%rdi
  14ded6:	0f 92 84 24 88 00 00 	setb   0x88(%rsp)
  14dedd:	00 
  14dede:	49 39 dc             	cmp    %rbx,%r12
  14dee1:	0f 97 c1             	seta   %cl
  14dee4:	4c 8d a4 24 e0 00 00 	lea    0xe0(%rsp),%r12
  14deeb:	00 
  14deec:	4d 39 fc             	cmp    %r15,%r12
  14deef:	41 0f 92 c7          	setb   %r15b
  14def3:	44 84 ac 24 98 00 00 	test   %r13b,0x98(%rsp)
  14defa:	00 
  14defb:	0f 85 c0 0d 00 00    	jne    14ecc1 <MultiSteersOdometer::CalSpeed()+0x1631>
  14df01:	44 22 84 24 90 00 00 	and    0x90(%rsp),%r8b
  14df08:	00 
  14df09:	4c 8b 64 24 38       	mov    0x38(%rsp),%r12
  14df0e:	0f 85 a6 00 00 00    	jne    14dfba <MultiSteersOdometer::CalSpeed()+0x92a>
  14df14:	44 22 9c 24 88 00 00 	and    0x88(%rsp),%r11b
  14df1b:	00 
  14df1c:	0f 85 98 00 00 00    	jne    14dfba <MultiSteersOdometer::CalSpeed()+0x92a>
  14df22:	44 20 f9             	and    %r15b,%cl
  14df25:	0f 85 8f 00 00 00    	jne    14dfba <MultiSteersOdometer::CalSpeed()+0x92a>
  14df2b:	4d 89 cb             	mov    %r9,%r11
  14df2e:	49 83 e3 fe          	and    $0xfffffffffffffffe,%r11
  14df32:	4c 01 da             	add    %r11,%rdx
MultiSteersOdometer::CalSpeed():
  14df35:	f2 0f 10 84 24 d0 00 	movsd  0xd0(%rsp),%xmm0
  14df3c:	00 00 
  14df3e:	f2 0f 10 8c 24 d8 00 	movsd  0xd8(%rsp),%xmm1
  14df45:	00 00 
  14df47:	66 0f 14 c0          	unpcklpd %xmm0,%xmm0
  14df4b:	66 0f 14 c9          	unpcklpd %xmm1,%xmm1
  14df4f:	f2 0f 10 94 24 e0 00 	movsd  0xe0(%rsp),%xmm2
  14df56:	00 00 
  14df58:	66 0f 14 d2          	unpcklpd %xmm2,%xmm2
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14df5c:	4d 89 d7             	mov    %r10,%r15
  14df5f:	49 c1 e7 04          	shl    $0x4,%r15
  14df63:	4c 89 d9             	mov    %r11,%rcx
Eigen::internal::mapbase_evaluator<Eigen::Block<Eigen::Matrix<double, -1, -1, 0, -1, -1> const, 1, -1, false>, Eigen::Matrix<double, 1, -1, 1, 1, -1> >::coeff(long, long) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14df66:	66 2e 0f 1f 84 00 00 	cs nopw 0x0(%rax,%rax,1)
  14df6d:	00 00 00 
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:834
  14df70:	66 0f 10 1f          	movupd (%rdi),%xmm3
  14df74:	66 0f 59 d8          	mulpd  %xmm0,%xmm3
  14df78:	66 42 0f 10 24 d7    	movupd (%rdi,%r10,8),%xmm4
  14df7e:	66 0f 59 e1          	mulpd  %xmm1,%xmm4
Eigen::internal::scalar_sum_op<double, double>::operator()(double const&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/BinaryFunctors.h:42
  14df82:	66 0f 58 e3          	addpd  %xmm3,%xmm4
Eigen::internal::mapbase_evaluator<Eigen::Block<Eigen::Matrix<double, -1, -1, 0, -1, -1> const, 1, -1, false>, Eigen::Matrix<double, 1, -1, 1, 1, -1> >::coeff(long, long) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:834
  14df86:	66 42 0f 10 1c 3f    	movupd (%rdi,%r15,1),%xmm3
  14df8c:	66 0f 59 da          	mulpd  %xmm2,%xmm3
Eigen::internal::scalar_sum_op<double, double>::operator()(double const&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/BinaryFunctors.h:42
  14df90:	66 0f 58 dc          	addpd  %xmm4,%xmm3
Eigen::internal::sub_assign_op<double, double>::assignCoeff(double&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/AssignmentFunctors.h:70
  14df94:	66 0f 10 23          	movupd (%rbx),%xmm4
  14df98:	66 0f 5c e3          	subpd  %xmm3,%xmm4
  14df9c:	66 0f 11 23          	movupd %xmm4,(%rbx)
  14dfa0:	48 83 c7 10          	add    $0x10,%rdi
  14dfa4:	48 83 c3 10          	add    $0x10,%rbx
  14dfa8:	48 83 c1 fe          	add    $0xfffffffffffffffe,%rcx
  14dfac:	75 c2                	jne    14df70 <MultiSteersOdometer::CalSpeed()+0x8e0>
MultiSteersOdometer::CalSpeed():
  14dfae:	4d 39 d9             	cmp    %r11,%r9
  14dfb1:	48 8b 4c 24 08       	mov    0x8(%rsp),%rcx
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14dfb6:	75 07                	jne    14dfbf <MultiSteersOdometer::CalSpeed()+0x92f>
  14dfb8:	eb 5f                	jmp    14e019 <MultiSteersOdometer::CalSpeed()+0x989>
MultiSteersOdometer::CalSpeed():
  14dfba:	48 8b 4c 24 08       	mov    0x8(%rsp),%rcx
Eigen::internal::evaluator<Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> > >::coeffRef(long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:187
  14dfbf:	48 8d 0c ce          	lea    (%rsi,%rcx,8),%rcx
  14dfc3:	4a 8d 3c d6          	lea    (%rsi,%r10,8),%rdi
Eigen::internal::mapbase_evaluator<Eigen::Block<Eigen::Matrix<double, -1, -1, 0, -1, -1> const, 1, -1, false>, Eigen::Matrix<double, 1, -1, 1, 1, -1> >::coeff(long, long) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:187
  14dfc7:	66 0f 1f 84 00 00 00 	nopw   0x0(%rax,%rax,1)
  14dfce:	00 00 
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:834
  14dfd0:	f2 0f 10 04 d6       	movsd  (%rsi,%rdx,8),%xmm0
Eigen::internal::scalar_product_op<double, double>::operator()(double const&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/BinaryFunctors.h:86
  14dfd5:	f2 0f 59 84 24 d0 00 	mulsd  0xd0(%rsp),%xmm0
  14dfdc:	00 00 
Eigen::internal::mapbase_evaluator<Eigen::Block<Eigen::Matrix<double, -1, -1, 0, -1, -1> const, 1, -1, false>, Eigen::Matrix<double, 1, -1, 1, 1, -1> >::coeff(long, long) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:834
  14dfde:	f2 0f 10 0c d7       	movsd  (%rdi,%rdx,8),%xmm1
Eigen::internal::scalar_product_op<double, double>::operator()(double const&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/BinaryFunctors.h:86
  14dfe3:	f2 0f 59 8c 24 d8 00 	mulsd  0xd8(%rsp),%xmm1
  14dfea:	00 00 
Eigen::internal::mapbase_evaluator<Eigen::Block<Eigen::Matrix<double, -1, -1, 0, -1, -1> const, 1, -1, false>, Eigen::Matrix<double, 1, -1, 1, 1, -1> >::coeff(long, long) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:834
  14dfec:	f2 0f 10 14 d1       	movsd  (%rcx,%rdx,8),%xmm2
Eigen::internal::scalar_product_op<double, double>::operator()(double const&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/BinaryFunctors.h:86
  14dff1:	f2 0f 59 94 24 e0 00 	mulsd  0xe0(%rsp),%xmm2
  14dff8:	00 00 
Eigen::internal::scalar_sum_op<double, double>::operator()(double const&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/BinaryFunctors.h:42
  14dffa:	f2 0f 58 c8          	addsd  %xmm0,%xmm1
  14dffe:	f2 0f 58 d1          	addsd  %xmm1,%xmm2
Eigen::internal::sub_assign_op<double, double>::assignCoeff(double&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/AssignmentFunctors.h:70
  14e002:	f2 0f 10 04 d0       	movsd  (%rax,%rdx,8),%xmm0
  14e007:	f2 0f 5c c2          	subsd  %xmm2,%xmm0
  14e00b:	f2 0f 11 04 d0       	movsd  %xmm0,(%rax,%rdx,8)
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, 1, 0, -1, 1> >, Eigen::internal::evaluator<Eigen::Product<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Matrix<double, 3, 1, 0, 3, 1>, 1> >, Eigen::internal::sub_assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14e010:	48 83 c2 01          	add    $0x1,%rdx
  14e014:	49 39 d6             	cmp    %rdx,%r14
  14e017:	75 b7                	jne    14dfd0 <MultiSteersOdometer::CalSpeed()+0x940>
Eigen::DenseStorage<double, -1, -1, 1, 0>::rows() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:544
  14e019:	4c 8b bc 24 a8 00 00 	mov    0xa8(%rsp),%r15
  14e020:	00 
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:137
  14e021:	4c 89 fb             	mov    %r15,%rbx
  14e024:	48 c1 eb 3f          	shr    $0x3f,%rbx
  14e028:	4c 01 fb             	add    %r15,%rbx
  14e02b:	48 d1 fb             	sar    %rbx
Eigen::DenseStorage<double, -1, -1, 1, 0>::DenseStorage():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:500
  14e02e:	66 0f 57 c0          	xorpd  %xmm0,%xmm0
  14e032:	66 0f 29 84 24 10 01 	movapd %xmm0,0x110(%rsp)
  14e039:	00 00 
Eigen::DenseStorage<double, -1, -1, 1, 0>::resize(long, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:553
  14e03b:	49 8d 47 01          	lea    0x1(%r15),%rax
  14e03f:	48 83 f8 03          	cmp    $0x3,%rax
  14e043:	0f 82 9d 00 00 00    	jb     14e0e6 <MultiSteersOdometer::CalSpeed()+0xa56>
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:556
  14e049:	49 83 ff 02          	cmp    $0x2,%r15
  14e04d:	0f 8c 87 00 00 00    	jl     14e0da <MultiSteersOdometer::CalSpeed()+0xa4a>
void Eigen::internal::check_size_for_overflow<double>(unsigned long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:288
  14e053:	48 89 d8             	mov    %rbx,%rax
  14e056:	48 c1 e8 3d          	shr    $0x3d,%rax
  14e05a:	0f 85 a0 0c 00 00    	jne    14ed00 <MultiSteersOdometer::CalSpeed()+0x1670>
double* Eigen::internal::conditional_aligned_new_auto<double, true>(unsigned long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:374
  14e060:	4c 8d 34 dd 00 00 00 	lea    0x0(,%rbx,8),%r14
  14e067:	00 
Eigen::internal::aligned_malloc(unsigned long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:159
  14e068:	4c 89 f7             	mov    %r14,%rdi
  14e06b:	e8 60 7c f3 ff       	call   85cd0 <malloc@plt>
  14e070:	48 89 c7             	mov    %rax,%rdi
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:167
  14e073:	4d 85 f6             	test   %r14,%r14
  14e076:	74 09                	je     14e081 <MultiSteersOdometer::CalSpeed()+0x9f1>
  14e078:	48 85 ff             	test   %rdi,%rdi
  14e07b:	0f 84 ad 0c 00 00    	je     14ed2e <MultiSteersOdometer::CalSpeed()+0x169e>
Eigen::DenseStorage<double, -1, -1, 1, 0>::resize(long, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:557
  14e081:	48 89 bc 24 10 01 00 	mov    %rdi,0x110(%rsp)
  14e088:	00 
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:562
  14e089:	48 89 9c 24 18 01 00 	mov    %rbx,0x118(%rsp)
  14e090:	00 
  14e091:	31 c0                	xor    %eax,%eax
  14e093:	48 89 d9             	mov    %rbx,%rcx
MultiSteersOdometer::CalSpeed():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:562
  14e096:	66 2e 0f 1f 84 00 00 	cs nopw 0x0(%rax,%rax,1)
  14e09d:	00 00 00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:139
  14e0a0:	89 c2                	mov    %eax,%edx
  14e0a2:	83 e2 fe             	and    $0xfffffffe,%edx
Eigen::DenseStorage<double, -1, -1, 1, 0>::data():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:565
  14e0a5:	48 8b b4 24 a0 00 00 	mov    0xa0(%rsp),%rsi
  14e0ac:	00 
double __vector(2) Eigen::internal::ploadu<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:336
  14e0ad:	66 0f 10 04 d6       	movupd (%rsi,%rdx,8),%xmm0
double __vector(2) Eigen::internal::pmul<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:226
  14e0b2:	66 0f 59 c0          	mulpd  %xmm0,%xmm0
Eigen::internal::unpacket_traits<double __vector(2)>::type Eigen::internal::predux<double __vector(2)>(double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:560
  14e0b6:	66 0f 28 c8          	movapd %xmm0,%xmm1
  14e0ba:	0f 12 c9             	movhlps %xmm1,%xmm1
  14e0bd:	f2 0f 58 c8          	addsd  %xmm0,%xmm1
double Eigen::numext::sqrt<double>(double const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/MathFunctions.h:554
  14e0c1:	f3 0f 7e c1          	movq   %xmm1,%xmm0
  14e0c5:	66 0f 51 c0          	sqrtpd %xmm0,%xmm0
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:139
  14e0c9:	66 0f 13 04 87       	movlpd %xmm0,(%rdi,%rax,4)
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:138
  14e0ce:	48 83 c0 02          	add    $0x2,%rax
  14e0d2:	48 83 c1 ff          	add    $0xffffffffffffffff,%rcx
  14e0d6:	75 c8                	jne    14e0a0 <MultiSteersOdometer::CalSpeed()+0xa10>
  14e0d8:	eb 16                	jmp    14e0f0 <MultiSteersOdometer::CalSpeed()+0xa60>
Eigen::DenseStorage<double, -1, -1, 1, 0>::resize(long, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:559
  14e0da:	48 c7 84 24 10 01 00 	movq   $0x0,0x110(%rsp)
  14e0e1:	00 00 00 00 00 
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:562
  14e0e6:	48 89 9c 24 18 01 00 	mov    %rbx,0x118(%rsp)
  14e0ed:	00 
  14e0ee:	31 ff                	xor    %edi,%edi
Eigen::internal::redux_impl<Eigen::internal::scalar_max_op<double, double>, Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> >, 3, 0>::run(Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> > const&, Eigen::internal::scalar_max_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/Redux.h:231
  14e0f0:	48 8d 43 01          	lea    0x1(%rbx),%rax
  14e0f4:	48 83 f8 03          	cmp    $0x3,%rax
  14e0f8:	0f 82 d1 01 00 00    	jb     14e2cf <MultiSteersOdometer::CalSpeed()+0xc3f>
MultiSteersOdometer::CalSpeed():
  14e0fe:	4c 89 f9             	mov    %r15,%rcx
  14e101:	48 c1 f9 3f          	sar    $0x3f,%rcx
  14e105:	48 89 c8             	mov    %rcx,%rax
  14e108:	48 c1 e8 3e          	shr    $0x3e,%rax
  14e10c:	4c 01 f8             	add    %r15,%rax
  14e10f:	48 c1 f8 02          	sar    $0x2,%rax
  14e113:	48 01 c0             	add    %rax,%rax
double __vector(2) Eigen::internal::pload<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:307
  14e116:	66 0f 28 07          	movapd (%rdi),%xmm0
double __vector(2) Eigen::internal::pabs<double __vector(2)>(double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:456
  14e11a:	66 0f 54 05 ae df 04 	andpd  0x4dfae(%rip),%xmm0        # 19c0d0 <typeinfo name for FollowErrorAndResponseMonitor+0x50>
  14e121:	00 
Eigen::internal::redux_impl<Eigen::internal::scalar_max_op<double, double>, Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> >, 3, 0>::run(Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> > const&, Eigen::internal::scalar_max_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/Redux.h:234
  14e122:	49 83 ff 08          	cmp    $0x8,%r15
  14e126:	0f 8c e8 00 00 00    	jl     14e214 <MultiSteersOdometer::CalSpeed()+0xb84>
MultiSteersOdometer::CalSpeed():
  14e12c:	48 c1 e9 3d          	shr    $0x3d,%rcx
  14e130:	4c 01 f9             	add    %r15,%rcx
  14e133:	48 c1 f9 03          	sar    $0x3,%rcx
  14e137:	48 c1 e1 02          	shl    $0x2,%rcx
double __vector(2) Eigen::internal::pload<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:307
  14e13b:	66 0f 28 4f 10       	movapd 0x10(%rdi),%xmm1
double __vector(2) Eigen::internal::pabs<double __vector(2)>(double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:456
  14e140:	66 0f 54 0d 88 df 04 	andpd  0x4df88(%rip),%xmm1        # 19c0d0 <typeinfo name for FollowErrorAndResponseMonitor+0x50>
  14e147:	00 
Eigen::internal::redux_impl<Eigen::internal::scalar_max_op<double, double>, Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> >, 3, 0>::run(Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> > const&, Eigen::internal::scalar_max_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/Redux.h:237
  14e148:	49 83 ff 10          	cmp    $0x10,%r15
  14e14c:	0f 8c a8 00 00 00    	jl     14e1fa <MultiSteersOdometer::CalSpeed()+0xb6a>
double __vector(2) Eigen::internal::evaluator<Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> > >::packet<16, double __vector(2)>(long) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:204
  14e152:	48 83 f9 07          	cmp    $0x7,%rcx
  14e156:	be 08 00 00 00       	mov    $0x8,%esi
  14e15b:	48 0f 4f f1          	cmovg  %rcx,%rsi
  14e15f:	48 83 c6 fb          	add    $0xfffffffffffffffb,%rsi
  14e163:	48 c1 ee 02          	shr    $0x2,%rsi
  14e167:	44 8d 46 01          	lea    0x1(%rsi),%r8d
  14e16b:	41 83 e0 01          	and    $0x1,%r8d
  14e16f:	48 85 f6             	test   %rsi,%rsi
  14e172:	0f 84 34 0b 00 00    	je     14ecac <MultiSteersOdometer::CalSpeed()+0x161c>
  14e178:	49 8d 50 ff          	lea    -0x1(%r8),%rdx
  14e17c:	48 29 f2             	sub    %rsi,%rdx
  14e17f:	31 f6                	xor    %esi,%esi
  14e181:	66 0f 28 15 47 df 04 	movapd 0x4df47(%rip),%xmm2        # 19c0d0 <typeinfo name for FollowErrorAndResponseMonitor+0x50>
  14e188:	00 
double __vector(2) Eigen::internal::unary_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const>, Eigen::internal::IndexBased, double>::packet<16, double __vector(2)>(long) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:204
  14e189:	0f 1f 80 00 00 00 00 	nopl   0x0(%rax)
MultiSteersOdometer::CalSpeed():
  14e190:	66 0f 28 5c f7 20    	movapd 0x20(%rdi,%rsi,8),%xmm3
double __vector(2) Eigen::internal::pabs<double __vector(2)>(double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:456
  14e196:	66 0f 54 da          	andpd  %xmm2,%xmm3
double __vector(2) Eigen::internal::pmax<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:267
  14e19a:	66 0f 5f c3          	maxpd  %xmm3,%xmm0
MultiSteersOdometer::CalSpeed():
  14e19e:	66 0f 28 5c f7 30    	movapd 0x30(%rdi,%rsi,8),%xmm3
double __vector(2) Eigen::internal::pabs<double __vector(2)>(double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:456
  14e1a4:	66 0f 54 da          	andpd  %xmm2,%xmm3
double __vector(2) Eigen::internal::pmax<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:267
  14e1a8:	66 0f 5f cb          	maxpd  %xmm3,%xmm1
MultiSteersOdometer::CalSpeed():
  14e1ac:	66 0f 28 5c f7 40    	movapd 0x40(%rdi,%rsi,8),%xmm3
double __vector(2) Eigen::internal::pabs<double __vector(2)>(double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:456
  14e1b2:	66 0f 54 da          	andpd  %xmm2,%xmm3
double __vector(2) Eigen::internal::pmax<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:267
  14e1b6:	66 0f 5f c3          	maxpd  %xmm3,%xmm0
MultiSteersOdometer::CalSpeed():
  14e1ba:	66 0f 28 5c f7 50    	movapd 0x50(%rdi,%rsi,8),%xmm3
double __vector(2) Eigen::internal::pabs<double __vector(2)>(double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:456
  14e1c0:	66 0f 54 da          	andpd  %xmm2,%xmm3
double __vector(2) Eigen::internal::pmax<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:267
  14e1c4:	66 0f 5f cb          	maxpd  %xmm3,%xmm1
Eigen::internal::redux_impl<Eigen::internal::scalar_max_op<double, double>, Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> >, 3, 0>::run(Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> > const&, Eigen::internal::scalar_max_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/Redux.h:237
  14e1c8:	48 83 c6 08          	add    $0x8,%rsi
  14e1cc:	48 83 c2 02          	add    $0x2,%rdx
  14e1d0:	75 be                	jne    14e190 <MultiSteersOdometer::CalSpeed()+0xb00>
  14e1d2:	48 8d 56 04          	lea    0x4(%rsi),%rdx
  14e1d6:	4d 85 c0             	test   %r8,%r8
  14e1d9:	74 1f                	je     14e1fa <MultiSteersOdometer::CalSpeed()+0xb6a>
double __vector(2) Eigen::internal::pabs<double __vector(2)>(double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:456
  14e1db:	66 0f 28 15 ed de 04 	movapd 0x4deed(%rip),%xmm2        # 19c0d0 <typeinfo name for FollowErrorAndResponseMonitor+0x50>
  14e1e2:	00 
  14e1e3:	66 0f 28 5c f7 30    	movapd 0x30(%rdi,%rsi,8),%xmm3
  14e1e9:	66 0f 54 da          	andpd  %xmm2,%xmm3
double __vector(2) Eigen::internal::pmax<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:267
  14e1ed:	66 0f 5f cb          	maxpd  %xmm3,%xmm1
double __vector(2) Eigen::internal::pabs<double __vector(2)>(double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:456
  14e1f1:	66 0f 54 14 d7       	andpd  (%rdi,%rdx,8),%xmm2
double __vector(2) Eigen::internal::pmax<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:267
  14e1f6:	66 0f 5f c2          	maxpd  %xmm2,%xmm0
  14e1fa:	66 0f 5f c1          	maxpd  %xmm1,%xmm0
Eigen::internal::redux_impl<Eigen::internal::scalar_max_op<double, double>, Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> >, 3, 0>::run(Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> > const&, Eigen::internal::scalar_max_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/Redux.h:244
  14e1fe:	48 39 c8             	cmp    %rcx,%rax
  14e201:	7e 11                	jle    14e214 <MultiSteersOdometer::CalSpeed()+0xb84>
double __vector(2) Eigen::internal::pload<double __vector(2)>(Eigen::internal::unpacket_traits<double __vector(2)>::type const*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:307
  14e203:	66 0f 28 0c cf       	movapd (%rdi,%rcx,8),%xmm1
double __vector(2) Eigen::internal::pabs<double __vector(2)>(double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:456
  14e208:	66 0f 54 0d c0 de 04 	andpd  0x4dec0(%rip),%xmm1        # 19c0d0 <typeinfo name for FollowErrorAndResponseMonitor+0x50>
  14e20f:	00 
double __vector(2) Eigen::internal::pmax<double __vector(2)>(double __vector(2) const&, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:267
  14e210:	66 0f 5f c1          	maxpd  %xmm1,%xmm0
Eigen::internal::unpacket_traits<double __vector(2)>::type Eigen::internal::predux_max<double __vector(2)>(double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:651
  14e214:	66 0f 28 c8          	movapd %xmm0,%xmm1
  14e218:	0f 12 c9             	movhlps %xmm1,%xmm1
  14e21b:	f2 0f 5f c1          	maxsd  %xmm1,%xmm0
Eigen::internal::redux_impl<Eigen::internal::scalar_max_op<double, double>, Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> >, 3, 0>::run(Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> > const&, Eigen::internal::scalar_max_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/Redux.h:252
  14e21f:	48 39 c3             	cmp    %rax,%rbx
  14e222:	0f 8e b3 00 00 00    	jle    14e2db <MultiSteersOdometer::CalSpeed()+0xc4b>
Eigen::internal::evaluator<Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> > >::coeff(long) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:172
  14e228:	89 da                	mov    %ebx,%edx
  14e22a:	29 c2                	sub    %eax,%edx
  14e22c:	48 8d 4b ff          	lea    -0x1(%rbx),%rcx
  14e230:	48 29 c1             	sub    %rax,%rcx
  14e233:	48 83 e2 03          	and    $0x3,%rdx
  14e237:	74 32                	je     14e26b <MultiSteersOdometer::CalSpeed()+0xbdb>
  14e239:	48 f7 da             	neg    %rdx
  14e23c:	66 0f 28 0d 8c de 04 	movapd 0x4de8c(%rip),%xmm1        # 19c0d0 <typeinfo name for FollowErrorAndResponseMonitor+0x50>
  14e243:	00 
  14e244:	66 0f 28 d0          	movapd %xmm0,%xmm2
std::abs(double):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:172
  14e248:	0f 1f 84 00 00 00 00 	nopl   0x0(%rax,%rax,1)
  14e24f:	00 
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_abs.h:71
  14e250:	f2 0f 10 04 c7       	movsd  (%rdi,%rax,8),%xmm0
  14e255:	66 0f 54 c1          	andpd  %xmm1,%xmm0
double Eigen::numext::maxi<double>(double const&, double const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/MathFunctions.h:829
  14e259:	f2 0f 5f c2          	maxsd  %xmm2,%xmm0
Eigen::internal::redux_impl<Eigen::internal::scalar_max_op<double, double>, Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> >, 3, 0>::run(Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> > const&, Eigen::internal::scalar_max_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/Redux.h:252
  14e25d:	48 83 c0 01          	add    $0x1,%rax
MultiSteersOdometer::CalSpeed():
  14e261:	66 0f 28 d0          	movapd %xmm0,%xmm2
Eigen::internal::redux_impl<Eigen::internal::scalar_max_op<double, double>, Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> >, 3, 0>::run(Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> > const&, Eigen::internal::scalar_max_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/Redux.h:252
  14e265:	48 83 c2 01          	add    $0x1,%rdx
  14e269:	75 e5                	jne    14e250 <MultiSteersOdometer::CalSpeed()+0xbc0>
Eigen::internal::evaluator<Eigen::PlainObjectBase<Eigen::Matrix<double, -1, 1, 0, -1, 1> > >::coeff(long) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:172
  14e26b:	48 83 f9 03          	cmp    $0x3,%rcx
  14e26f:	72 6a                	jb     14e2db <MultiSteersOdometer::CalSpeed()+0xc4b>
  14e271:	48 29 c3             	sub    %rax,%rbx
  14e274:	48 8d 04 c7          	lea    (%rdi,%rax,8),%rax
  14e278:	48 83 c0 18          	add    $0x18,%rax
  14e27c:	66 0f 28 0d 4c de 04 	movapd 0x4de4c(%rip),%xmm1        # 19c0d0 <typeinfo name for FollowErrorAndResponseMonitor+0x50>
  14e283:	00 
std::abs(double):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:172
  14e284:	66 66 66 2e 0f 1f 84 	data16 data16 cs nopw 0x0(%rax,%rax,1)
  14e28b:	00 00 00 00 00 
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_abs.h:71
  14e290:	f2 0f 10 50 e8       	movsd  -0x18(%rax),%xmm2
  14e295:	f2 0f 10 58 f0       	movsd  -0x10(%rax),%xmm3
  14e29a:	66 0f 54 d1          	andpd  %xmm1,%xmm2
double Eigen::numext::maxi<double>(double const&, double const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/MathFunctions.h:829
  14e29e:	f2 0f 5f d0          	maxsd  %xmm0,%xmm2
std::abs(double):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_abs.h:71
  14e2a2:	66 0f 54 d9          	andpd  %xmm1,%xmm3
double Eigen::numext::maxi<double>(double const&, double const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/MathFunctions.h:829
  14e2a6:	f2 0f 5f da          	maxsd  %xmm2,%xmm3
std::abs(double):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_abs.h:71
  14e2aa:	f2 0f 10 50 f8       	movsd  -0x8(%rax),%xmm2
  14e2af:	66 0f 54 d1          	andpd  %xmm1,%xmm2
double Eigen::numext::maxi<double>(double const&, double const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/MathFunctions.h:829
  14e2b3:	f2 0f 5f d3          	maxsd  %xmm3,%xmm2
std::abs(double):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_abs.h:71
  14e2b7:	f2 0f 10 00          	movsd  (%rax),%xmm0
  14e2bb:	66 0f 54 c1          	andpd  %xmm1,%xmm0
double Eigen::numext::maxi<double>(double const&, double const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/MathFunctions.h:829
  14e2bf:	f2 0f 5f c2          	maxsd  %xmm2,%xmm0
Eigen::internal::redux_impl<Eigen::internal::scalar_max_op<double, double>, Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> >, 3, 0>::run(Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> > const&, Eigen::internal::scalar_max_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/Redux.h:252
  14e2c3:	48 83 c0 20          	add    $0x20,%rax
  14e2c7:	48 83 c3 fc          	add    $0xfffffffffffffffc,%rbx
  14e2cb:	75 c3                	jne    14e290 <MultiSteersOdometer::CalSpeed()+0xc00>
  14e2cd:	eb 0c                	jmp    14e2db <MultiSteersOdometer::CalSpeed()+0xc4b>
std::abs(double):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_abs.h:71
  14e2cf:	f2 0f 10 07          	movsd  (%rdi),%xmm0
  14e2d3:	66 0f 54 05 f5 dd 04 	andpd  0x4ddf5(%rip),%xmm0        # 19c0d0 <typeinfo name for FollowErrorAndResponseMonitor+0x50>
  14e2da:	00 
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:142
  14e2db:	66 41 0f 2e 84 24 40 	ucomisd 0x140(%r12),%xmm0
  14e2e2:	01 00 00 
  14e2e5:	41 0f 96 44 24 0e    	setbe  0xe(%r12)
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:144
  14e2eb:	41 80 7c 24 0c 00    	cmpb   $0x0,0xc(%r12)
  14e2f1:	0f 84 2c 09 00 00    	je     14ec23 <MultiSteersOdometer::CalSpeed()+0x1593>
  14e2f7:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  14e2fe:	00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:145
  14e2ff:	be 18 00 00 00       	mov    $0x18,%esi
  14e304:	e8 c7 61 f3 ff       	call   844d0 <std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::basic_stringstream(std::_Ios_Openmode)@plt>
  14e309:	48 8d 9c 24 50 01 00 	lea    0x150(%rsp),%rbx
  14e310:	00 
std::basic_ostream<char, std::char_traits<char> >& std::operator<< <std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ostream:561
  14e311:	48 8d 35 73 1f 05 00 	lea    0x51f73(%rip),%rsi        # 1a028b <typeinfo name for rbk::Logger::Thread::move2thread<DualDiffOdometer::CaldPose()::$_4>(DualDiffOdometer::CaldPose()::$_4&&)::{lambda()#1}+0x70b>
  14e318:	ba 05 00 00 00       	mov    $0x5,%edx
  14e31d:	48 89 df             	mov    %rbx,%rdi
  14e320:	e8 9b 7e f3 ff       	call   861c0 <std::basic_ostream<char, std::char_traits<char> >& std::__ostream_insert<char, std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*, long)@plt>
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:145
  14e325:	48 8d 44 24 70       	lea    0x70(%rsp),%rax
  14e32a:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
  14e32f:	48 8d 74 24 10       	lea    0x10(%rsp),%rsi
  14e334:	48 89 df             	mov    %rbx,%rdi
  14e337:	e8 24 73 f3 ff       	call   85660 <std::ostream& Eigen::operator<< <Eigen::Transpose<Eigen::Matrix<double, -1, 1, 0, -1, 1> > >(std::ostream&, Eigen::DenseBase<Eigen::Transpose<Eigen::Matrix<double, -1, 1, 0, -1, 1> > > const&)@plt>
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::str() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:779
  14e33c:	48 8d b4 24 58 01 00 	lea    0x158(%rsp),%rsi
  14e343:	00 
  14e344:	48 8d bc 24 20 01 00 	lea    0x120(%rsp),%rdi
  14e34b:	00 
  14e34c:	e8 af 5f f3 ff       	call   84300 <std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::str() const@plt>
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:145
  14e351:	e8 8a 5b f3 ff       	call   83ee0 <rbk::Logger::thread()@plt>
  14e356:	49 89 c6             	mov    %rax,%r14
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:182
  14e359:	4c 8d 64 24 50       	lea    0x50(%rsp),%r12
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14e35e:	4c 89 64 24 40       	mov    %r12,0x40(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14e363:	4c 8b bc 24 20 01 00 	mov    0x120(%rsp),%r15
  14e36a:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14e36b:	48 8b 9c 24 28 01 00 	mov    0x128(%rsp),%rbx
  14e372:	00 
bool __gnu_cxx::__is_null_pointer<char>(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/type_traits.h:153
  14e373:	4d 85 ff             	test   %r15,%r15
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:211
  14e376:	75 09                	jne    14e381 <MultiSteersOdometer::CalSpeed()+0xcf1>
  14e378:	48 85 db             	test   %rbx,%rbx
  14e37b:	0f 85 67 09 00 00    	jne    14ece8 <MultiSteersOdometer::CalSpeed()+0x1658>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:215
  14e381:	48 89 5c 24 10       	mov    %rbx,0x10(%rsp)
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:217
  14e386:	48 83 fb 0f          	cmp    $0xf,%rbx
  14e38a:	76 32                	jbe    14e3be <MultiSteersOdometer::CalSpeed()+0xd2e>
MultiSteersOdometer::CalSpeed():
  14e38c:	48 8d 7c 24 40       	lea    0x40(%rsp),%rdi
  14e391:	48 8d 74 24 10       	lea    0x10(%rsp),%rsi
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:219
  14e396:	31 d2                	xor    %edx,%edx
  14e398:	e8 93 6d f3 ff       	call   85130 <std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_create(unsigned long&, unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14e39d:	48 89 44 24 40       	mov    %rax,0x40(%rsp)
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:220
  14e3a2:	48 8b 4c 24 10       	mov    0x10(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14e3a7:	48 89 4c 24 50       	mov    %rcx,0x50(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  14e3ac:	48 85 db             	test   %rbx,%rbx
  14e3af:	74 25                	je     14e3d6 <MultiSteersOdometer::CalSpeed()+0xd46>
  14e3b1:	48 83 fb 01          	cmp    $0x1,%rbx
  14e3b5:	75 11                	jne    14e3c8 <MultiSteersOdometer::CalSpeed()+0xd38>
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14e3b7:	41 8a 0f             	mov    (%r15),%cl
  14e3ba:	88 08                	mov    %cl,(%rax)
  14e3bc:	eb 18                	jmp    14e3d6 <MultiSteersOdometer::CalSpeed()+0xd46>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14e3be:	4c 89 e0             	mov    %r12,%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  14e3c1:	48 85 db             	test   %rbx,%rbx
  14e3c4:	75 eb                	jne    14e3b1 <MultiSteersOdometer::CalSpeed()+0xd21>
  14e3c6:	eb 0e                	jmp    14e3d6 <MultiSteersOdometer::CalSpeed()+0xd46>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14e3c8:	48 89 c7             	mov    %rax,%rdi
  14e3cb:	4c 89 fe             	mov    %r15,%rsi
  14e3ce:	48 89 da             	mov    %rbx,%rdx
  14e3d1:	e8 9a 50 f3 ff       	call   83470 <memcpy@plt>
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:232
  14e3d6:	48 8b 44 24 10       	mov    0x10(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14e3db:	48 89 44 24 48       	mov    %rax,0x48(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14e3e0:	48 8b 4c 24 40       	mov    0x40(%rsp),%rcx
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14e3e5:	c6 04 01 00          	movb   $0x0,(%rcx,%rax,1)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:182
  14e3e9:	4c 8d 6c 24 20       	lea    0x20(%rsp),%r13
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14e3ee:	4c 89 6c 24 10       	mov    %r13,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14e3f3:	48 8b 5c 24 40       	mov    0x40(%rsp),%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14e3f8:	4c 39 e3             	cmp    %r12,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:534
  14e3fb:	74 11                	je     14e40e <MultiSteersOdometer::CalSpeed()+0xd7e>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14e3fd:	48 89 5c 24 10       	mov    %rbx,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:542
  14e402:	48 8b 44 24 50       	mov    0x50(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14e407:	48 89 44 24 20       	mov    %rax,0x20(%rsp)
  14e40c:	eb 0f                	jmp    14e41d <MultiSteersOdometer::CalSpeed()+0xd8d>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14e40e:	66 41 0f 10 04 24    	movupd (%r12),%xmm0
  14e414:	66 41 0f 11 45 00    	movupd %xmm0,0x0(%r13)
  14e41a:	4c 89 eb             	mov    %r13,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14e41d:	4c 8b 7c 24 48       	mov    0x48(%rsp),%r15
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14e422:	4c 89 7c 24 18       	mov    %r15,0x18(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14e427:	4c 89 64 24 40       	mov    %r12,0x40(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14e42c:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  14e433:	00 00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14e435:	c6 44 24 50 00       	movb   $0x0,0x50(%rsp)
std::_Function_base::_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:271
  14e43a:	48 c7 84 24 c0 00 00 	movq   $0x0,0xc0(%rsp)
  14e441:	00 00 00 00 00 
std::_Function_base::_Base_manager<std::_Bind<MultiSteersOdometer::CalSpeed()::$_2 ()> >::_M_init_functor(std::_Any_data&, std::_Bind<MultiSteersOdometer::CalSpeed()::$_2 ()>&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14e446:	bf 28 00 00 00       	mov    $0x28,%edi
  14e44b:	e8 70 52 f3 ff       	call   836c0 <operator new(unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:182
  14e450:	48 89 c1             	mov    %rax,%rcx
  14e453:	48 83 c1 10          	add    $0x10,%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14e457:	48 89 08             	mov    %rcx,(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14e45a:	4c 39 eb             	cmp    %r13,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:534
  14e45d:	74 0e                	je     14e46d <MultiSteersOdometer::CalSpeed()+0xddd>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14e45f:	48 89 18             	mov    %rbx,(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:542
  14e462:	48 8b 4c 24 20       	mov    0x20(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14e467:	48 89 48 10          	mov    %rcx,0x10(%rax)
  14e46b:	eb 0a                	jmp    14e477 <MultiSteersOdometer::CalSpeed()+0xde7>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14e46d:	66 41 0f 10 45 00    	movupd 0x0(%r13),%xmm0
  14e473:	66 0f 11 01          	movupd %xmm0,(%rcx)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14e477:	4c 89 6c 24 10       	mov    %r13,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14e47c:	48 c7 44 24 18 00 00 	movq   $0x0,0x18(%rsp)
  14e483:	00 00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14e485:	c6 44 24 20 00       	movb   $0x0,0x20(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14e48a:	4c 89 78 08          	mov    %r15,0x8(%rax)
std::_Function_base::_Base_manager<std::_Bind<MultiSteersOdometer::CalSpeed()::$_2 ()> >::_M_init_functor(std::_Any_data&, std::_Bind<MultiSteersOdometer::CalSpeed()::$_2 ()>&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14e48e:	48 89 84 24 b0 00 00 	mov    %rax,0xb0(%rsp)
  14e495:	00 
std::function<void ()>::function<std::_Bind<MultiSteersOdometer::CalSpeed()::$_2 ()>, void, void>(std::_Bind<MultiSteersOdometer::CalSpeed()::$_2 ()>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:694
  14e496:	48 8d 05 a3 22 00 00 	lea    0x22a3(%rip),%rax        # 150740 <std::_Function_handler<void (), std::_Bind<MultiSteersOdometer::CalSpeed()::$_2 ()> >::_M_invoke(std::_Any_data const&)>
  14e49d:	48 89 84 24 c8 00 00 	mov    %rax,0xc8(%rsp)
  14e4a4:	00 
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:695
  14e4a5:	48 8d 05 74 24 00 00 	lea    0x2474(%rip),%rax        # 150920 <std::_Function_base::_Base_manager<std::_Bind<MultiSteersOdometer::CalSpeed()::$_2 ()> >::_M_manager(std::_Any_data&, std::_Any_data const&, std::_Manager_operation)>
  14e4ac:	48 89 84 24 c0 00 00 	mov    %rax,0xc0(%rsp)
  14e4b3:	00 
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1294
  14e4b4:	48 c7 44 24 60 00 00 	movq   $0x0,0x60(%rsp)
  14e4bb:	00 00 
  14e4bd:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
MultiSteersOdometer::CalSpeed():
  14e4c2:	48 8d 94 24 f0 00 00 	lea    0xf0(%rsp),%rdx
  14e4c9:	00 
  14e4ca:	48 8d 8c 24 b0 00 00 	lea    0xb0(%rsp),%rcx
  14e4d1:	00 
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1294
  14e4d2:	31 f6                	xor    %esi,%esi
  14e4d4:	e8 67 86 f3 ff       	call   86b40 <std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count<std::packaged_task<void ()>, std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::packaged_task<void ()>*, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&)@plt>
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_get_deleter(std::type_info const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:727
  14e4d9:	48 8b 7c 24 68       	mov    0x68(%rsp),%rdi
  14e4de:	48 85 ff             	test   %rdi,%rdi
  14e4e1:	74 17                	je     14e4fa <MultiSteersOdometer::CalSpeed()+0xe6a>
  14e4e3:	48 8b 07             	mov    (%rdi),%rax
  14e4e6:	48 8b 35 63 93 2b 00 	mov    0x2b9363(%rip),%rsi        # 407850 <typeinfo for std::_Sp_make_shared_tag@@Base+0x6d08>
  14e4ed:	ff 50 20             	call   *0x20(%rax)
  14e4f0:	48 89 c3             	mov    %rax,%rbx
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:688
  14e4f3:	4c 8b 7c 24 68       	mov    0x68(%rsp),%r15
  14e4f8:	eb 05                	jmp    14e4ff <MultiSteersOdometer::CalSpeed()+0xe6f>
MultiSteersOdometer::CalSpeed():
  14e4fa:	45 31 ff             	xor    %r15d,%r15d
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_get_deleter(std::type_info const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:727
  14e4fd:	31 db                	xor    %ebx,%ebx
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1300
  14e4ff:	48 89 5c 24 60       	mov    %rbx,0x60(%rsp)
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:690
  14e504:	4d 85 ff             	test   %r15,%r15
  14e507:	74 17                	je     14e520 <MultiSteersOdometer::CalSpeed()+0xe90>
__gnu_cxx::__atomic_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:95
  14e509:	48 83 3d 97 95 2b 00 	cmpq   $0x0,0x2b9597(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14e510:	00 
  14e511:	74 08                	je     14e51b <MultiSteersOdometer::CalSpeed()+0xe8b>
__gnu_cxx::__atomic_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:53
  14e513:	f0 41 83 47 08 01    	lock addl $0x1,0x8(%r15)
  14e519:	eb 05                	jmp    14e520 <MultiSteersOdometer::CalSpeed()+0xe90>
__gnu_cxx::__atomic_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:74
  14e51b:	41 83 47 08 01       	addl   $0x1,0x8(%r15)
std::_Function_base::_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:271
  14e520:	48 c7 84 24 00 01 00 	movq   $0x0,0x100(%rsp)
  14e527:	00 00 00 00 00 
std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_2>(MultiSteersOdometer::CalSpeed()::$_2&&)::{lambda()#1}>::_M_init_functor(std::_Any_data&, rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_2>(MultiSteersOdometer::CalSpeed()::$_2&&)::{lambda()#1}&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14e52c:	bf 10 00 00 00       	mov    $0x10,%edi
  14e531:	e8 8a 51 f3 ff       	call   836c0 <operator new(unsigned long)@plt>
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr(std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1131
  14e536:	48 89 18             	mov    %rbx,(%rax)
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_swap(std::__shared_count<(__gnu_cxx::_Lock_policy)2>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:714
  14e539:	4c 89 78 08          	mov    %r15,0x8(%rax)
std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_2>(MultiSteersOdometer::CalSpeed()::$_2&&)::{lambda()#1}>::_M_init_functor(std::_Any_data&, rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_2>(MultiSteersOdometer::CalSpeed()::$_2&&)::{lambda()#1}&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14e53d:	48 89 84 24 f0 00 00 	mov    %rax,0xf0(%rsp)
  14e544:	00 
std::function<void ()>::function<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_2>(MultiSteersOdometer::CalSpeed()::$_2&&)::{lambda()#1}, void, void>(rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_2>(MultiSteersOdometer::CalSpeed()::$_2&&)::{lambda()#1}):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:694
  14e545:	48 8d 05 04 25 00 00 	lea    0x2504(%rip),%rax        # 150a50 <std::_Function_handler<void (), rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_2>(MultiSteersOdometer::CalSpeed()::$_2&&)::{lambda()#1}>::_M_invoke(std::_Any_data const&)>
  14e54c:	48 89 84 24 08 01 00 	mov    %rax,0x108(%rsp)
  14e553:	00 
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:695
  14e554:	48 8d 05 25 25 00 00 	lea    0x2525(%rip),%rax        # 150a80 <std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_2>(MultiSteersOdometer::CalSpeed()::$_2&&)::{lambda()#1}>::_M_manager(std::_Any_data&, std::_Any_data const&, std::_Manager_operation)>
  14e55b:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  14e562:	00 
std::future<decltype ({parm#1}({parm#2}...))> rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_2>(MultiSteersOdometer::CalSpeed()::$_2&&):
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:204
  14e563:	49 8d 7e 08          	lea    0x8(%r14),%rdi
  14e567:	48 8d b4 24 f0 00 00 	lea    0xf0(%rsp),%rsi
  14e56e:	00 
  14e56f:	e8 3c 58 f3 ff       	call   83db0 <rbk::Logger::Thread::SafeQueue<std::function<void ()> >::push_back(std::function<void ()>&)@plt>
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:206
  14e574:	49 81 c6 c0 01 00 00 	add    $0x1c0,%r14
  14e57b:	4c 89 f7             	mov    %r14,%rdi
  14e57e:	e8 2d 67 f3 ff       	call   84cb0 <std::condition_variable::notify_one()@plt>
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::get() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1258
  14e583:	48 8b 74 24 60       	mov    0x60(%rsp),%rsi
  14e588:	48 8d bc 24 d8 02 00 	lea    0x2d8(%rsp),%rdi
  14e58f:	00 
std::future<decltype ({parm#1}({parm#2}...))> rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_2>(MultiSteersOdometer::CalSpeed()::$_2&&):
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:207
  14e590:	e8 bb 79 f3 ff       	call   85f50 <std::packaged_task<void ()>::get_future()@plt>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14e595:	48 8b 84 24 00 01 00 	mov    0x100(%rsp),%rax
  14e59c:	00 
  14e59d:	48 85 c0             	test   %rax,%rax
  14e5a0:	74 12                	je     14e5b4 <MultiSteersOdometer::CalSpeed()+0xf24>
MultiSteersOdometer::CalSpeed():
  14e5a2:	48 8d bc 24 f0 00 00 	lea    0xf0(%rsp),%rdi
  14e5a9:	00 
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14e5aa:	ba 03 00 00 00       	mov    $0x3,%edx
  14e5af:	48 89 fe             	mov    %rdi,%rsi
  14e5b2:	ff d0                	call   *%rax
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14e5b4:	48 8b 5c 24 68       	mov    0x68(%rsp),%rbx
  14e5b9:	48 85 db             	test   %rbx,%rbx
  14e5bc:	74 58                	je     14e616 <MultiSteersOdometer::CalSpeed()+0xf86>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14e5be:	48 83 3d e2 94 2b 00 	cmpq   $0x0,0x2b94e2(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14e5c5:	00 
  14e5c6:	74 11                	je     14e5d9 <MultiSteersOdometer::CalSpeed()+0xf49>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14e5c8:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14e5cd:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14e5d2:	83 f8 01             	cmp    $0x1,%eax
  14e5d5:	74 10                	je     14e5e7 <MultiSteersOdometer::CalSpeed()+0xf57>
  14e5d7:	eb 3d                	jmp    14e616 <MultiSteersOdometer::CalSpeed()+0xf86>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14e5d9:	8b 43 08             	mov    0x8(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14e5dc:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14e5df:	89 4b 08             	mov    %ecx,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14e5e2:	83 f8 01             	cmp    $0x1,%eax
  14e5e5:	75 2f                	jne    14e616 <MultiSteersOdometer::CalSpeed()+0xf86>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14e5e7:	48 8b 03             	mov    (%rbx),%rax
  14e5ea:	48 89 df             	mov    %rbx,%rdi
  14e5ed:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14e5f0:	48 83 3d b0 94 2b 00 	cmpq   $0x0,0x2b94b0(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14e5f7:	00 
  14e5f8:	0f 84 52 06 00 00    	je     14ec50 <MultiSteersOdometer::CalSpeed()+0x15c0>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14e5fe:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14e603:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14e608:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14e60b:	75 09                	jne    14e616 <MultiSteersOdometer::CalSpeed()+0xf86>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14e60d:	48 8b 03             	mov    (%rbx),%rax
  14e610:	48 89 df             	mov    %rbx,%rdi
  14e613:	ff 50 18             	call   *0x18(%rax)
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14e616:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  14e61d:	00 
  14e61e:	48 85 c0             	test   %rax,%rax
  14e621:	74 12                	je     14e635 <MultiSteersOdometer::CalSpeed()+0xfa5>
MultiSteersOdometer::CalSpeed():
  14e623:	48 8d bc 24 b0 00 00 	lea    0xb0(%rsp),%rdi
  14e62a:	00 
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14e62b:	ba 03 00 00 00       	mov    $0x3,%edx
  14e630:	48 89 fe             	mov    %rdi,%rsi
  14e633:	ff d0                	call   *%rax
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14e635:	48 8b 9c 24 e0 02 00 	mov    0x2e0(%rsp),%rbx
  14e63c:	00 
  14e63d:	48 85 db             	test   %rbx,%rbx
  14e640:	74 58                	je     14e69a <MultiSteersOdometer::CalSpeed()+0x100a>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14e642:	48 83 3d 5e 94 2b 00 	cmpq   $0x0,0x2b945e(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14e649:	00 
  14e64a:	74 11                	je     14e65d <MultiSteersOdometer::CalSpeed()+0xfcd>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14e64c:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14e651:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14e656:	83 f8 01             	cmp    $0x1,%eax
  14e659:	74 10                	je     14e66b <MultiSteersOdometer::CalSpeed()+0xfdb>
  14e65b:	eb 3d                	jmp    14e69a <MultiSteersOdometer::CalSpeed()+0x100a>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14e65d:	8b 43 08             	mov    0x8(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14e660:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14e663:	89 4b 08             	mov    %ecx,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14e666:	83 f8 01             	cmp    $0x1,%eax
  14e669:	75 2f                	jne    14e69a <MultiSteersOdometer::CalSpeed()+0x100a>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14e66b:	48 8b 03             	mov    (%rbx),%rax
  14e66e:	48 89 df             	mov    %rbx,%rdi
  14e671:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14e674:	48 83 3d 2c 94 2b 00 	cmpq   $0x0,0x2b942c(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14e67b:	00 
  14e67c:	0f 84 e5 05 00 00    	je     14ec67 <MultiSteersOdometer::CalSpeed()+0x15d7>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14e682:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14e687:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14e68c:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14e68f:	75 09                	jne    14e69a <MultiSteersOdometer::CalSpeed()+0x100a>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14e691:	48 8b 03             	mov    (%rbx),%rax
  14e694:	48 89 df             	mov    %rbx,%rdi
  14e697:	ff 50 18             	call   *0x18(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14e69a:	48 8b 7c 24 40       	mov    0x40(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14e69f:	4c 39 e7             	cmp    %r12,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14e6a2:	74 05                	je     14e6a9 <MultiSteersOdometer::CalSpeed()+0x1019>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14e6a4:	e8 87 63 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14e6a9:	48 8b bc 24 20 01 00 	mov    0x120(%rsp),%rdi
  14e6b0:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14e6b1:	48 8d 84 24 30 01 00 	lea    0x130(%rsp),%rax
  14e6b8:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14e6b9:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14e6bc:	74 05                	je     14e6c3 <MultiSteersOdometer::CalSpeed()+0x1033>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14e6be:	e8 6d 63 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::~basic_stringstream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:731
  14e6c3:	48 8b 1d 9e 93 2b 00 	mov    0x2b939e(%rip),%rbx        # 407a68 <VTT for std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  14e6ca:	48 8b 03             	mov    (%rbx),%rax
  14e6cd:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  14e6d4:	00 
  14e6d5:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  14e6d9:	48 89 84 24 90 00 00 	mov    %rax,0x90(%rsp)
  14e6e0:	00 
  14e6e1:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14e6e5:	48 89 8c 24 88 00 00 	mov    %rcx,0x88(%rsp)
  14e6ec:	00 
  14e6ed:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  14e6f4:	00 
  14e6f5:	48 8b 43 48          	mov    0x48(%rbx),%rax
  14e6f9:	48 89 84 24 e8 00 00 	mov    %rax,0xe8(%rsp)
  14e700:	00 
  14e701:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  14e708:	00 
std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::~basic_stringbuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/sstream.tcc:291
  14e709:	4c 8b 25 58 87 2b 00 	mov    0x2b8758(%rip),%r12        # 406e68 <vtable for std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  14e710:	49 83 c4 10          	add    $0x10,%r12
  14e714:	4c 89 a4 24 58 01 00 	mov    %r12,0x158(%rsp)
  14e71b:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14e71c:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  14e723:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14e724:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  14e72b:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14e72c:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14e72f:	74 05                	je     14e736 <MultiSteersOdometer::CalSpeed()+0x10a6>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14e731:	e8 fa 62 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::basic_streambuf<char, std::char_traits<char> >::~basic_streambuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/streambuf:198
  14e736:	48 8b 05 db 91 2b 00 	mov    0x2b91db(%rip),%rax        # 407918 <vtable for std::basic_streambuf<char, std::char_traits<char> >@GLIBCXX_3.4>
  14e73d:	48 83 c0 10          	add    $0x10,%rax
  14e741:	48 89 84 24 98 00 00 	mov    %rax,0x98(%rsp)
  14e748:	00 
  14e749:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  14e750:	00 
  14e751:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  14e758:	00 
  14e759:	e8 d2 7a f3 ff       	call   86230 <std::locale::~locale()@plt>
std::basic_istream<char, std::char_traits<char> >::~basic_istream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/istream:104
  14e75e:	48 8b 43 10          	mov    0x10(%rbx),%rax
  14e762:	48 8b 5b 18          	mov    0x18(%rbx),%rbx
  14e766:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  14e76d:	00 
  14e76e:	48 89 44 24 08       	mov    %rax,0x8(%rsp)
  14e773:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14e777:	48 89 9c 04 40 01 00 	mov    %rbx,0x140(%rsp,%rax,1)
  14e77e:	00 
  14e77f:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  14e786:	00 00 00 00 00 
std::basic_ios<char, std::char_traits<char> >::~basic_ios():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:282
  14e78b:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  14e792:	00 
  14e793:	e8 88 6b f3 ff       	call   85320 <std::ios_base::~ios_base()@plt>
  14e798:	48 8d bc 24 40 01 00 	lea    0x140(%rsp),%rdi
  14e79f:	00 
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:146
  14e7a0:	be 18 00 00 00       	mov    $0x18,%esi
  14e7a5:	e8 26 5d f3 ff       	call   844d0 <std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::basic_stringstream(std::_Ios_Openmode)@plt>
  14e7aa:	4c 8d b4 24 50 01 00 	lea    0x150(%rsp),%r14
  14e7b1:	00 
std::basic_ostream<char, std::char_traits<char> >& std::operator<< <std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ostream:561
  14e7b2:	48 8d 35 d8 1a 05 00 	lea    0x51ad8(%rip),%rsi        # 1a0291 <typeinfo name for rbk::Logger::Thread::move2thread<DualDiffOdometer::CaldPose()::$_4>(DualDiffOdometer::CaldPose()::$_4&&)::{lambda()#1}+0x711>
  14e7b9:	ba 0b 00 00 00       	mov    $0xb,%edx
  14e7be:	4c 89 f7             	mov    %r14,%rdi
  14e7c1:	48 89 5c 24 38       	mov    %rbx,0x38(%rsp)
  14e7c6:	e8 f5 79 f3 ff       	call   861c0 <std::basic_ostream<char, std::char_traits<char> >& std::__ostream_insert<char, std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*, long)@plt>
MultiSteersOdometer::CalSpeed():
  14e7cb:	48 8d 84 24 10 01 00 	lea    0x110(%rsp),%rax
  14e7d2:	00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:146
  14e7d3:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
  14e7d8:	48 8d 74 24 10       	lea    0x10(%rsp),%rsi
  14e7dd:	4c 89 f7             	mov    %r14,%rdi
  14e7e0:	e8 7b 6e f3 ff       	call   85660 <std::ostream& Eigen::operator<< <Eigen::Transpose<Eigen::Matrix<double, -1, 1, 0, -1, 1> > >(std::ostream&, Eigen::DenseBase<Eigen::Transpose<Eigen::Matrix<double, -1, 1, 0, -1, 1> > > const&)@plt>
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::str() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:779
  14e7e5:	48 8d b4 24 58 01 00 	lea    0x158(%rsp),%rsi
  14e7ec:	00 
  14e7ed:	48 8d bc 24 20 01 00 	lea    0x120(%rsp),%rdi
  14e7f4:	00 
  14e7f5:	e8 06 5b f3 ff       	call   84300 <std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::str() const@plt>
MultiSteersOdometer::CalSpeed():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:146
  14e7fa:	e8 e1 56 f3 ff       	call   83ee0 <rbk::Logger::thread()@plt>
  14e7ff:	49 89 c6             	mov    %rax,%r14
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14e802:	48 8d 44 24 50       	lea    0x50(%rsp),%rax
  14e807:	48 89 44 24 40       	mov    %rax,0x40(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14e80c:	4c 8b bc 24 20 01 00 	mov    0x120(%rsp),%r15
  14e813:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14e814:	48 8b 9c 24 28 01 00 	mov    0x128(%rsp),%rbx
  14e81b:	00 
bool __gnu_cxx::__is_null_pointer<char>(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/type_traits.h:153
  14e81c:	4d 85 ff             	test   %r15,%r15
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:211
  14e81f:	75 09                	jne    14e82a <MultiSteersOdometer::CalSpeed()+0x119a>
  14e821:	48 85 db             	test   %rbx,%rbx
  14e824:	0f 85 ca 04 00 00    	jne    14ecf4 <MultiSteersOdometer::CalSpeed()+0x1664>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:215
  14e82a:	48 89 5c 24 10       	mov    %rbx,0x10(%rsp)
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:217
  14e82f:	48 83 fb 0f          	cmp    $0xf,%rbx
  14e833:	76 32                	jbe    14e867 <MultiSteersOdometer::CalSpeed()+0x11d7>
MultiSteersOdometer::CalSpeed():
  14e835:	48 8d 7c 24 40       	lea    0x40(%rsp),%rdi
  14e83a:	48 8d 74 24 10       	lea    0x10(%rsp),%rsi
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:219
  14e83f:	31 d2                	xor    %edx,%edx
  14e841:	e8 ea 68 f3 ff       	call   85130 <std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_create(unsigned long&, unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14e846:	48 89 44 24 40       	mov    %rax,0x40(%rsp)
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:220
  14e84b:	48 8b 4c 24 10       	mov    0x10(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14e850:	48 89 4c 24 50       	mov    %rcx,0x50(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  14e855:	48 85 db             	test   %rbx,%rbx
  14e858:	74 27                	je     14e881 <MultiSteersOdometer::CalSpeed()+0x11f1>
  14e85a:	48 83 fb 01          	cmp    $0x1,%rbx
  14e85e:	75 13                	jne    14e873 <MultiSteersOdometer::CalSpeed()+0x11e3>
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14e860:	41 8a 0f             	mov    (%r15),%cl
  14e863:	88 08                	mov    %cl,(%rax)
  14e865:	eb 1a                	jmp    14e881 <MultiSteersOdometer::CalSpeed()+0x11f1>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14e867:	48 8d 44 24 50       	lea    0x50(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  14e86c:	48 85 db             	test   %rbx,%rbx
  14e86f:	75 e9                	jne    14e85a <MultiSteersOdometer::CalSpeed()+0x11ca>
  14e871:	eb 0e                	jmp    14e881 <MultiSteersOdometer::CalSpeed()+0x11f1>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14e873:	48 89 c7             	mov    %rax,%rdi
  14e876:	4c 89 fe             	mov    %r15,%rsi
  14e879:	48 89 da             	mov    %rbx,%rdx
  14e87c:	e8 ef 4b f3 ff       	call   83470 <memcpy@plt>
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:232
  14e881:	48 8b 44 24 10       	mov    0x10(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14e886:	48 89 44 24 48       	mov    %rax,0x48(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14e88b:	48 8b 4c 24 40       	mov    0x40(%rsp),%rcx
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14e890:	c6 04 01 00          	movb   $0x0,(%rcx,%rax,1)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14e894:	4c 89 6c 24 10       	mov    %r13,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14e899:	48 8b 5c 24 40       	mov    0x40(%rsp),%rbx
MultiSteersOdometer::CalSpeed():
  14e89e:	48 8d 4c 24 50       	lea    0x50(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14e8a3:	48 39 cb             	cmp    %rcx,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:534
  14e8a6:	74 11                	je     14e8b9 <MultiSteersOdometer::CalSpeed()+0x1229>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14e8a8:	48 89 5c 24 10       	mov    %rbx,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:542
  14e8ad:	48 8b 44 24 50       	mov    0x50(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14e8b2:	48 89 44 24 20       	mov    %rax,0x20(%rsp)
  14e8b7:	eb 0d                	jmp    14e8c6 <MultiSteersOdometer::CalSpeed()+0x1236>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14e8b9:	66 0f 10 01          	movupd (%rcx),%xmm0
  14e8bd:	66 41 0f 11 45 00    	movupd %xmm0,0x0(%r13)
  14e8c3:	4c 89 eb             	mov    %r13,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14e8c6:	4c 8b 7c 24 48       	mov    0x48(%rsp),%r15
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14e8cb:	4c 89 7c 24 18       	mov    %r15,0x18(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14e8d0:	48 89 4c 24 40       	mov    %rcx,0x40(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14e8d5:	48 c7 44 24 48 00 00 	movq   $0x0,0x48(%rsp)
  14e8dc:	00 00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14e8de:	c6 44 24 50 00       	movb   $0x0,0x50(%rsp)
std::_Function_base::_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:271
  14e8e3:	48 c7 84 24 c0 00 00 	movq   $0x0,0xc0(%rsp)
  14e8ea:	00 00 00 00 00 
std::_Function_base::_Base_manager<std::_Bind<MultiSteersOdometer::CalSpeed()::$_3 ()> >::_M_init_functor(std::_Any_data&, std::_Bind<MultiSteersOdometer::CalSpeed()::$_3 ()>&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14e8ef:	bf 28 00 00 00       	mov    $0x28,%edi
  14e8f4:	e8 c7 4d f3 ff       	call   836c0 <operator new(unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:182
  14e8f9:	48 89 c1             	mov    %rax,%rcx
  14e8fc:	48 83 c1 10          	add    $0x10,%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14e900:	48 89 08             	mov    %rcx,(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14e903:	4c 39 eb             	cmp    %r13,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:534
  14e906:	74 0e                	je     14e916 <MultiSteersOdometer::CalSpeed()+0x1286>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14e908:	48 89 18             	mov    %rbx,(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:542
  14e90b:	48 8b 4c 24 20       	mov    0x20(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14e910:	48 89 48 10          	mov    %rcx,0x10(%rax)
  14e914:	eb 0a                	jmp    14e920 <MultiSteersOdometer::CalSpeed()+0x1290>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14e916:	66 41 0f 10 45 00    	movupd 0x0(%r13),%xmm0
  14e91c:	66 0f 11 01          	movupd %xmm0,(%rcx)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14e920:	4c 89 6c 24 10       	mov    %r13,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14e925:	48 c7 44 24 18 00 00 	movq   $0x0,0x18(%rsp)
  14e92c:	00 00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14e92e:	c6 44 24 20 00       	movb   $0x0,0x20(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14e933:	4c 89 78 08          	mov    %r15,0x8(%rax)
std::_Function_base::_Base_manager<std::_Bind<MultiSteersOdometer::CalSpeed()::$_3 ()> >::_M_init_functor(std::_Any_data&, std::_Bind<MultiSteersOdometer::CalSpeed()::$_3 ()>&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14e937:	48 89 84 24 b0 00 00 	mov    %rax,0xb0(%rsp)
  14e93e:	00 
std::function<void ()>::function<std::_Bind<MultiSteersOdometer::CalSpeed()::$_3 ()>, void, void>(std::_Bind<MultiSteersOdometer::CalSpeed()::$_3 ()>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:694
  14e93f:	48 8d 05 5a 22 00 00 	lea    0x225a(%rip),%rax        # 150ba0 <std::_Function_handler<void (), std::_Bind<MultiSteersOdometer::CalSpeed()::$_3 ()> >::_M_invoke(std::_Any_data const&)>
  14e946:	48 89 84 24 c8 00 00 	mov    %rax,0xc8(%rsp)
  14e94d:	00 
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:695
  14e94e:	48 8d 05 2b 24 00 00 	lea    0x242b(%rip),%rax        # 150d80 <std::_Function_base::_Base_manager<std::_Bind<MultiSteersOdometer::CalSpeed()::$_3 ()> >::_M_manager(std::_Any_data&, std::_Any_data const&, std::_Manager_operation)>
  14e955:	48 89 84 24 c0 00 00 	mov    %rax,0xc0(%rsp)
  14e95c:	00 
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1294
  14e95d:	48 c7 44 24 60 00 00 	movq   $0x0,0x60(%rsp)
  14e964:	00 00 
  14e966:	48 8d 7c 24 68       	lea    0x68(%rsp),%rdi
MultiSteersOdometer::CalSpeed():
  14e96b:	48 8d 94 24 f0 00 00 	lea    0xf0(%rsp),%rdx
  14e972:	00 
  14e973:	48 8d 8c 24 b0 00 00 	lea    0xb0(%rsp),%rcx
  14e97a:	00 
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1294
  14e97b:	31 f6                	xor    %esi,%esi
  14e97d:	e8 be 81 f3 ff       	call   86b40 <std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count<std::packaged_task<void ()>, std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::packaged_task<void ()>*, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&)@plt>
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_get_deleter(std::type_info const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:727
  14e982:	48 8b 7c 24 68       	mov    0x68(%rsp),%rdi
  14e987:	48 85 ff             	test   %rdi,%rdi
  14e98a:	74 17                	je     14e9a3 <MultiSteersOdometer::CalSpeed()+0x1313>
  14e98c:	48 8b 07             	mov    (%rdi),%rax
  14e98f:	48 8b 35 ba 8e 2b 00 	mov    0x2b8eba(%rip),%rsi        # 407850 <typeinfo for std::_Sp_make_shared_tag@@Base+0x6d08>
  14e996:	ff 50 20             	call   *0x20(%rax)
  14e999:	48 89 c3             	mov    %rax,%rbx
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:688
  14e99c:	4c 8b 7c 24 68       	mov    0x68(%rsp),%r15
  14e9a1:	eb 05                	jmp    14e9a8 <MultiSteersOdometer::CalSpeed()+0x1318>
MultiSteersOdometer::CalSpeed():
  14e9a3:	45 31 ff             	xor    %r15d,%r15d
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_get_deleter(std::type_info const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:727
  14e9a6:	31 db                	xor    %ebx,%ebx
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1300
  14e9a8:	48 89 5c 24 60       	mov    %rbx,0x60(%rsp)
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:690
  14e9ad:	4d 85 ff             	test   %r15,%r15
  14e9b0:	74 17                	je     14e9c9 <MultiSteersOdometer::CalSpeed()+0x1339>
__gnu_cxx::__atomic_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:95
  14e9b2:	48 83 3d ee 90 2b 00 	cmpq   $0x0,0x2b90ee(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14e9b9:	00 
  14e9ba:	74 08                	je     14e9c4 <MultiSteersOdometer::CalSpeed()+0x1334>
__gnu_cxx::__atomic_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:53
  14e9bc:	f0 41 83 47 08 01    	lock addl $0x1,0x8(%r15)
  14e9c2:	eb 05                	jmp    14e9c9 <MultiSteersOdometer::CalSpeed()+0x1339>
__gnu_cxx::__atomic_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:74
  14e9c4:	41 83 47 08 01       	addl   $0x1,0x8(%r15)
std::_Function_base::_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:271
  14e9c9:	48 c7 84 24 00 01 00 	movq   $0x0,0x100(%rsp)
  14e9d0:	00 00 00 00 00 
std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_3>(MultiSteersOdometer::CalSpeed()::$_3&&)::{lambda()#1}>::_M_init_functor(std::_Any_data&, rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_3>(MultiSteersOdometer::CalSpeed()::$_3&&)::{lambda()#1}&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14e9d5:	bf 10 00 00 00       	mov    $0x10,%edi
  14e9da:	e8 e1 4c f3 ff       	call   836c0 <operator new(unsigned long)@plt>
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr(std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1131
  14e9df:	48 89 18             	mov    %rbx,(%rax)
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_swap(std::__shared_count<(__gnu_cxx::_Lock_policy)2>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:714
  14e9e2:	4c 89 78 08          	mov    %r15,0x8(%rax)
std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_3>(MultiSteersOdometer::CalSpeed()::$_3&&)::{lambda()#1}>::_M_init_functor(std::_Any_data&, rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_3>(MultiSteersOdometer::CalSpeed()::$_3&&)::{lambda()#1}&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14e9e6:	48 89 84 24 f0 00 00 	mov    %rax,0xf0(%rsp)
  14e9ed:	00 
std::function<void ()>::function<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_3>(MultiSteersOdometer::CalSpeed()::$_3&&)::{lambda()#1}, void, void>(rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_3>(MultiSteersOdometer::CalSpeed()::$_3&&)::{lambda()#1}):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:694
  14e9ee:	48 8d 05 bb 24 00 00 	lea    0x24bb(%rip),%rax        # 150eb0 <std::_Function_handler<void (), rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_3>(MultiSteersOdometer::CalSpeed()::$_3&&)::{lambda()#1}>::_M_invoke(std::_Any_data const&)>
  14e9f5:	48 89 84 24 08 01 00 	mov    %rax,0x108(%rsp)
  14e9fc:	00 
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:695
  14e9fd:	48 8d 05 dc 24 00 00 	lea    0x24dc(%rip),%rax        # 150ee0 <std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_3>(MultiSteersOdometer::CalSpeed()::$_3&&)::{lambda()#1}>::_M_manager(std::_Any_data&, std::_Any_data const&, std::_Manager_operation)>
  14ea04:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  14ea0b:	00 
std::future<decltype ({parm#1}({parm#2}...))> rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_3>(MultiSteersOdometer::CalSpeed()::$_3&&):
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:204
  14ea0c:	49 8d 7e 08          	lea    0x8(%r14),%rdi
  14ea10:	48 8d b4 24 f0 00 00 	lea    0xf0(%rsp),%rsi
  14ea17:	00 
  14ea18:	e8 93 53 f3 ff       	call   83db0 <rbk::Logger::Thread::SafeQueue<std::function<void ()> >::push_back(std::function<void ()>&)@plt>
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:206
  14ea1d:	49 81 c6 c0 01 00 00 	add    $0x1c0,%r14
  14ea24:	4c 89 f7             	mov    %r14,%rdi
  14ea27:	e8 84 62 f3 ff       	call   84cb0 <std::condition_variable::notify_one()@plt>
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::get() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1258
  14ea2c:	48 8b 74 24 60       	mov    0x60(%rsp),%rsi
  14ea31:	48 8d bc 24 c8 02 00 	lea    0x2c8(%rsp),%rdi
  14ea38:	00 
std::future<decltype ({parm#1}({parm#2}...))> rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalSpeed()::$_3>(MultiSteersOdometer::CalSpeed()::$_3&&):
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:207
  14ea39:	e8 12 75 f3 ff       	call   85f50 <std::packaged_task<void ()>::get_future()@plt>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14ea3e:	48 8b 84 24 00 01 00 	mov    0x100(%rsp),%rax
  14ea45:	00 
  14ea46:	48 85 c0             	test   %rax,%rax
  14ea49:	4c 8d bc 24 30 01 00 	lea    0x130(%rsp),%r15
  14ea50:	00 
  14ea51:	74 12                	je     14ea65 <MultiSteersOdometer::CalSpeed()+0x13d5>
MultiSteersOdometer::CalSpeed():
  14ea53:	48 8d bc 24 f0 00 00 	lea    0xf0(%rsp),%rdi
  14ea5a:	00 
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14ea5b:	ba 03 00 00 00       	mov    $0x3,%edx
  14ea60:	48 89 fe             	mov    %rdi,%rsi
  14ea63:	ff d0                	call   *%rax
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14ea65:	48 8b 5c 24 68       	mov    0x68(%rsp),%rbx
  14ea6a:	48 85 db             	test   %rbx,%rbx
  14ea6d:	4c 8b 74 24 38       	mov    0x38(%rsp),%r14
  14ea72:	74 58                	je     14eacc <MultiSteersOdometer::CalSpeed()+0x143c>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14ea74:	48 83 3d 2c 90 2b 00 	cmpq   $0x0,0x2b902c(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14ea7b:	00 
  14ea7c:	74 11                	je     14ea8f <MultiSteersOdometer::CalSpeed()+0x13ff>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14ea7e:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14ea83:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14ea88:	83 f8 01             	cmp    $0x1,%eax
  14ea8b:	74 10                	je     14ea9d <MultiSteersOdometer::CalSpeed()+0x140d>
  14ea8d:	eb 3d                	jmp    14eacc <MultiSteersOdometer::CalSpeed()+0x143c>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14ea8f:	8b 43 08             	mov    0x8(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14ea92:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14ea95:	89 4b 08             	mov    %ecx,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14ea98:	83 f8 01             	cmp    $0x1,%eax
  14ea9b:	75 2f                	jne    14eacc <MultiSteersOdometer::CalSpeed()+0x143c>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14ea9d:	48 8b 03             	mov    (%rbx),%rax
  14eaa0:	48 89 df             	mov    %rbx,%rdi
  14eaa3:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14eaa6:	48 83 3d fa 8f 2b 00 	cmpq   $0x0,0x2b8ffa(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14eaad:	00 
  14eaae:	0f 84 ca 01 00 00    	je     14ec7e <MultiSteersOdometer::CalSpeed()+0x15ee>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14eab4:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14eab9:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14eabe:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14eac1:	75 09                	jne    14eacc <MultiSteersOdometer::CalSpeed()+0x143c>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14eac3:	48 8b 03             	mov    (%rbx),%rax
  14eac6:	48 89 df             	mov    %rbx,%rdi
  14eac9:	ff 50 18             	call   *0x18(%rax)
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14eacc:	48 8b 84 24 c0 00 00 	mov    0xc0(%rsp),%rax
  14ead3:	00 
  14ead4:	48 85 c0             	test   %rax,%rax
  14ead7:	74 12                	je     14eaeb <MultiSteersOdometer::CalSpeed()+0x145b>
MultiSteersOdometer::CalSpeed():
  14ead9:	48 8d bc 24 b0 00 00 	lea    0xb0(%rsp),%rdi
  14eae0:	00 
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14eae1:	ba 03 00 00 00       	mov    $0x3,%edx
  14eae6:	48 89 fe             	mov    %rdi,%rsi
  14eae9:	ff d0                	call   *%rax
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14eaeb:	48 8b 9c 24 d0 02 00 	mov    0x2d0(%rsp),%rbx
  14eaf2:	00 
  14eaf3:	48 85 db             	test   %rbx,%rbx
  14eaf6:	74 58                	je     14eb50 <MultiSteersOdometer::CalSpeed()+0x14c0>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14eaf8:	48 83 3d a8 8f 2b 00 	cmpq   $0x0,0x2b8fa8(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14eaff:	00 
  14eb00:	74 11                	je     14eb13 <MultiSteersOdometer::CalSpeed()+0x1483>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14eb02:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14eb07:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14eb0c:	83 f8 01             	cmp    $0x1,%eax
  14eb0f:	74 10                	je     14eb21 <MultiSteersOdometer::CalSpeed()+0x1491>
  14eb11:	eb 3d                	jmp    14eb50 <MultiSteersOdometer::CalSpeed()+0x14c0>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14eb13:	8b 43 08             	mov    0x8(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14eb16:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14eb19:	89 4b 08             	mov    %ecx,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14eb1c:	83 f8 01             	cmp    $0x1,%eax
  14eb1f:	75 2f                	jne    14eb50 <MultiSteersOdometer::CalSpeed()+0x14c0>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14eb21:	48 8b 03             	mov    (%rbx),%rax
  14eb24:	48 89 df             	mov    %rbx,%rdi
  14eb27:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14eb2a:	48 83 3d 76 8f 2b 00 	cmpq   $0x0,0x2b8f76(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14eb31:	00 
  14eb32:	0f 84 5d 01 00 00    	je     14ec95 <MultiSteersOdometer::CalSpeed()+0x1605>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14eb38:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14eb3d:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14eb42:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14eb45:	75 09                	jne    14eb50 <MultiSteersOdometer::CalSpeed()+0x14c0>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14eb47:	48 8b 03             	mov    (%rbx),%rax
  14eb4a:	48 89 df             	mov    %rbx,%rdi
  14eb4d:	ff 50 18             	call   *0x18(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14eb50:	48 8b 7c 24 40       	mov    0x40(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14eb55:	48 8d 44 24 50       	lea    0x50(%rsp),%rax
  14eb5a:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14eb5d:	74 05                	je     14eb64 <MultiSteersOdometer::CalSpeed()+0x14d4>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14eb5f:	e8 cc 5e f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14eb64:	48 8b bc 24 20 01 00 	mov    0x120(%rsp),%rdi
  14eb6b:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14eb6c:	4c 39 ff             	cmp    %r15,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14eb6f:	74 05                	je     14eb76 <MultiSteersOdometer::CalSpeed()+0x14e6>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14eb71:	e8 ba 5e f3 ff       	call   84a30 <operator delete(void*)@plt>
MultiSteersOdometer::CalSpeed():
  14eb76:	48 8b 84 24 90 00 00 	mov    0x90(%rsp),%rax
  14eb7d:	00 
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::~basic_stringstream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:731
  14eb7e:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  14eb85:	00 
  14eb86:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14eb8a:	48 8b 8c 24 88 00 00 	mov    0x88(%rsp),%rcx
  14eb91:	00 
  14eb92:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  14eb99:	00 
  14eb9a:	48 8b 84 24 e8 00 00 	mov    0xe8(%rsp),%rax
  14eba1:	00 
  14eba2:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  14eba9:	00 
std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::~basic_stringbuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/sstream.tcc:291
  14ebaa:	4c 89 a4 24 58 01 00 	mov    %r12,0x158(%rsp)
  14ebb1:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14ebb2:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  14ebb9:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14ebba:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  14ebc1:	00 
  14ebc2:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14ebc5:	74 05                	je     14ebcc <MultiSteersOdometer::CalSpeed()+0x153c>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14ebc7:	e8 64 5e f3 ff       	call   84a30 <operator delete(void*)@plt>
std::basic_streambuf<char, std::char_traits<char> >::~basic_streambuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/streambuf:198
  14ebcc:	48 8b 84 24 98 00 00 	mov    0x98(%rsp),%rax
  14ebd3:	00 
  14ebd4:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  14ebdb:	00 
  14ebdc:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  14ebe3:	00 
  14ebe4:	e8 47 76 f3 ff       	call   86230 <std::locale::~locale()@plt>
  14ebe9:	48 8b 44 24 08       	mov    0x8(%rsp),%rax
std::basic_istream<char, std::char_traits<char> >::~basic_istream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/istream:104
  14ebee:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  14ebf5:	00 
  14ebf6:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14ebfa:	4c 89 b4 04 40 01 00 	mov    %r14,0x140(%rsp,%rax,1)
  14ec01:	00 
  14ec02:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  14ec09:	00 00 00 00 00 
std::basic_ios<char, std::char_traits<char> >::~basic_ios():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:282
  14ec0e:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  14ec15:	00 
  14ec16:	e8 05 67 f3 ff       	call   85320 <std::ios_base::~ios_base()@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::~DenseStorage():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:542
  14ec1b:	48 8b bc 24 10 01 00 	mov    0x110(%rsp),%rdi
  14ec22:	00 
Eigen::internal::aligned_free(void*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:177
  14ec23:	e8 48 4b f3 ff       	call   83770 <free@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::~DenseStorage():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:542
  14ec28:	48 8b bc 24 a0 00 00 	mov    0xa0(%rsp),%rdi
  14ec2f:	00 
Eigen::internal::aligned_free(void*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:177
  14ec30:	e8 3b 4b f3 ff       	call   83770 <free@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::~DenseStorage():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:542
  14ec35:	48 8b 7c 24 70       	mov    0x70(%rsp),%rdi
Eigen::internal::aligned_free(void*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:177
  14ec3a:	e8 31 4b f3 ff       	call   83770 <free@plt>
MultiSteersOdometer::CalSpeed():
  14ec3f:	b0 01                	mov    $0x1,%al
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:156
  14ec41:	48 8d 65 d8          	lea    -0x28(%rbp),%rsp
  14ec45:	5b                   	pop    %rbx
  14ec46:	41 5c                	pop    %r12
  14ec48:	41 5d                	pop    %r13
  14ec4a:	41 5e                	pop    %r14
  14ec4c:	41 5f                	pop    %r15
  14ec4e:	5d                   	pop    %rbp
  14ec4f:	c3                   	ret    
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14ec50:	8b 43 0c             	mov    0xc(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14ec53:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14ec56:	89 4b 0c             	mov    %ecx,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14ec59:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14ec5c:	0f 85 b4 f9 ff ff    	jne    14e616 <MultiSteersOdometer::CalSpeed()+0xf86>
  14ec62:	e9 a6 f9 ff ff       	jmp    14e60d <MultiSteersOdometer::CalSpeed()+0xf7d>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14ec67:	8b 43 0c             	mov    0xc(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14ec6a:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14ec6d:	89 4b 0c             	mov    %ecx,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14ec70:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14ec73:	0f 85 21 fa ff ff    	jne    14e69a <MultiSteersOdometer::CalSpeed()+0x100a>
  14ec79:	e9 13 fa ff ff       	jmp    14e691 <MultiSteersOdometer::CalSpeed()+0x1001>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14ec7e:	8b 43 0c             	mov    0xc(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14ec81:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14ec84:	89 4b 0c             	mov    %ecx,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14ec87:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14ec8a:	0f 85 3c fe ff ff    	jne    14eacc <MultiSteersOdometer::CalSpeed()+0x143c>
  14ec90:	e9 2e fe ff ff       	jmp    14eac3 <MultiSteersOdometer::CalSpeed()+0x1433>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14ec95:	8b 43 0c             	mov    0xc(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14ec98:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14ec9b:	89 4b 0c             	mov    %ecx,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14ec9e:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14eca1:	0f 85 a9 fe ff ff    	jne    14eb50 <MultiSteersOdometer::CalSpeed()+0x14c0>
  14eca7:	e9 9b fe ff ff       	jmp    14eb47 <MultiSteersOdometer::CalSpeed()+0x14b7>
MultiSteersOdometer::CalSpeed():
  14ecac:	31 f6                	xor    %esi,%esi
  14ecae:	ba 04 00 00 00       	mov    $0x4,%edx
Eigen::internal::redux_impl<Eigen::internal::scalar_max_op<double, double>, Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> >, 3, 0>::run(Eigen::internal::redux_evaluator<Eigen::CwiseUnaryOp<Eigen::internal::scalar_abs_op<double>, Eigen::ArrayWrapper<Eigen::Matrix<double, -1, 1, 0, -1, 1> > const> > const&, Eigen::internal::scalar_max_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/Redux.h:237
  14ecb3:	4d 85 c0             	test   %r8,%r8
  14ecb6:	0f 84 3e f5 ff ff    	je     14e1fa <MultiSteersOdometer::CalSpeed()+0xb6a>
  14ecbc:	e9 1a f5 ff ff       	jmp    14e1db <MultiSteersOdometer::CalSpeed()+0xb4b>
MultiSteersOdometer::CalSpeed():
  14ecc1:	4c 8b 64 24 38       	mov    0x38(%rsp),%r12
  14ecc6:	48 8b 4c 24 08       	mov    0x8(%rsp),%rcx
  14eccb:	e9 ef f2 ff ff       	jmp    14dfbf <MultiSteersOdometer::CalSpeed()+0x92f>
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:212
  14ecd0:	48 8d 3d de ed 03 00 	lea    0x3edde(%rip),%rdi        # 18dab5 <typeinfo name for rbk::Logger::Thread::move2thread<OdoCalculator::run()::$_32>(OdoCalculator::run()::$_32&&)::{lambda()#1}+0x1755>
  14ecd7:	e8 54 46 f3 ff       	call   83330 <std::__throw_logic_error(char const*)@plt>
  14ecdc:	48 8d 3d d2 ed 03 00 	lea    0x3edd2(%rip),%rdi        # 18dab5 <typeinfo name for rbk::Logger::Thread::move2thread<OdoCalculator::run()::$_32>(OdoCalculator::run()::$_32&&)::{lambda()#1}+0x1755>
  14ece3:	e8 48 46 f3 ff       	call   83330 <std::__throw_logic_error(char const*)@plt>
  14ece8:	48 8d 3d c6 ed 03 00 	lea    0x3edc6(%rip),%rdi        # 18dab5 <typeinfo name for rbk::Logger::Thread::move2thread<OdoCalculator::run()::$_32>(OdoCalculator::run()::$_32&&)::{lambda()#1}+0x1755>
  14ecef:	e8 3c 46 f3 ff       	call   83330 <std::__throw_logic_error(char const*)@plt>
  14ecf4:	48 8d 3d ba ed 03 00 	lea    0x3edba(%rip),%rdi        # 18dab5 <typeinfo name for rbk::Logger::Thread::move2thread<OdoCalculator::run()::$_32>(OdoCalculator::run()::$_32&&)::{lambda()#1}+0x1755>
  14ecfb:	e8 30 46 f3 ff       	call   83330 <std::__throw_logic_error(char const*)@plt>
Eigen::internal::throw_std_bad_alloc():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:70
  14ed00:	bf 08 00 00 00       	mov    $0x8,%edi
  14ed05:	e8 c6 55 f3 ff       	call   842d0 <__cxa_allocate_exception@plt>
std::bad_alloc::bad_alloc():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/new:57
  14ed0a:	48 8b 0d bf 83 2b 00 	mov    0x2b83bf(%rip),%rcx        # 4070d0 <vtable for std::bad_alloc@GLIBCXX_3.4>
  14ed11:	48 83 c1 10          	add    $0x10,%rcx
  14ed15:	48 89 08             	mov    %rcx,(%rax)
Eigen::internal::throw_std_bad_alloc():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:70
  14ed18:	48 8b 35 b9 85 2b 00 	mov    0x2b85b9(%rip),%rsi        # 4072d8 <typeinfo for std::bad_alloc@GLIBCXX_3.4>
  14ed1f:	48 8b 15 3a 7e 2b 00 	mov    0x2b7e3a(%rip),%rdx        # 406b60 <std::bad_alloc::~bad_alloc()@GLIBCXX_3.4>
  14ed26:	48 89 c7             	mov    %rax,%rdi
  14ed29:	e8 f2 60 f3 ff       	call   84e20 <__cxa_throw@plt>
  14ed2e:	bf 08 00 00 00       	mov    $0x8,%edi
  14ed33:	e8 98 55 f3 ff       	call   842d0 <__cxa_allocate_exception@plt>
std::bad_alloc::bad_alloc():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/new:57
  14ed38:	48 8b 0d 91 83 2b 00 	mov    0x2b8391(%rip),%rcx        # 4070d0 <vtable for std::bad_alloc@GLIBCXX_3.4>
  14ed3f:	48 83 c1 10          	add    $0x10,%rcx
  14ed43:	48 89 08             	mov    %rcx,(%rax)
Eigen::internal::throw_std_bad_alloc():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:70
  14ed46:	48 8b 35 8b 85 2b 00 	mov    0x2b858b(%rip),%rsi        # 4072d8 <typeinfo for std::bad_alloc@GLIBCXX_3.4>
  14ed4d:	48 8b 15 0c 7e 2b 00 	mov    0x2b7e0c(%rip),%rdx        # 406b60 <std::bad_alloc::~bad_alloc()@GLIBCXX_3.4>
  14ed54:	48 89 c7             	mov    %rax,%rdi
  14ed57:	e8 c4 60 f3 ff       	call   84e20 <__cxa_throw@plt>
MultiSteersOdometer::CalSpeed():
  14ed5c:	e9 d3 01 00 00       	jmp    14ef34 <MultiSteersOdometer::CalSpeed()+0x18a4>
  14ed61:	49 89 c6             	mov    %rax,%r14
  14ed64:	e9 7d 05 00 00       	jmp    14f2e6 <MultiSteersOdometer::CalSpeed()+0x1c56>
  14ed69:	49 89 c6             	mov    %rax,%r14
  14ed6c:	e9 63 05 00 00       	jmp    14f2d4 <MultiSteersOdometer::CalSpeed()+0x1c44>
  14ed71:	e9 cf 00 00 00       	jmp    14ee45 <MultiSteersOdometer::CalSpeed()+0x17b5>
  14ed76:	e9 99 01 00 00       	jmp    14ef14 <MultiSteersOdometer::CalSpeed()+0x1884>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14ed7b:	48 89 c7             	mov    %rax,%rdi
  14ed7e:	e8 1d 80 f5 ff       	call   a6da0 <__clang_call_terminate>
  14ed83:	48 89 c7             	mov    %rax,%rdi
  14ed86:	e8 15 80 f5 ff       	call   a6da0 <__clang_call_terminate>
  14ed8b:	48 89 c7             	mov    %rax,%rdi
  14ed8e:	e8 0d 80 f5 ff       	call   a6da0 <__clang_call_terminate>
  14ed93:	48 89 c7             	mov    %rax,%rdi
  14ed96:	e8 05 80 f5 ff       	call   a6da0 <__clang_call_terminate>
MultiSteersOdometer::CalSpeed():
  14ed9b:	49 89 c6             	mov    %rax,%r14
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:690
  14ed9e:	4d 85 ff             	test   %r15,%r15
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14eda1:	0f 84 bf 01 00 00    	je     14ef66 <MultiSteersOdometer::CalSpeed()+0x18d6>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14eda7:	48 83 3d f9 8c 2b 00 	cmpq   $0x0,0x2b8cf9(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14edae:	00 
  14edaf:	74 15                	je     14edc6 <MultiSteersOdometer::CalSpeed()+0x1736>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14edb1:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14edb6:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14edbc:	83 f8 01             	cmp    $0x1,%eax
  14edbf:	74 19                	je     14edda <MultiSteersOdometer::CalSpeed()+0x174a>
  14edc1:	e9 a0 01 00 00       	jmp    14ef66 <MultiSteersOdometer::CalSpeed()+0x18d6>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14edc6:	41 8b 47 08          	mov    0x8(%r15),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14edca:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14edcd:	41 89 4f 08          	mov    %ecx,0x8(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14edd1:	83 f8 01             	cmp    $0x1,%eax
  14edd4:	0f 85 8c 01 00 00    	jne    14ef66 <MultiSteersOdometer::CalSpeed()+0x18d6>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14edda:	49 8b 07             	mov    (%r15),%rax
  14eddd:	4c 89 ff             	mov    %r15,%rdi
  14ede0:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14ede3:	48 83 3d bd 8c 2b 00 	cmpq   $0x0,0x2b8cbd(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14edea:	00 
  14edeb:	74 15                	je     14ee02 <MultiSteersOdometer::CalSpeed()+0x1772>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14eded:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14edf2:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14edf8:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14edfb:	74 19                	je     14ee16 <MultiSteersOdometer::CalSpeed()+0x1786>
  14edfd:	e9 64 01 00 00       	jmp    14ef66 <MultiSteersOdometer::CalSpeed()+0x18d6>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14ee02:	41 8b 47 0c          	mov    0xc(%r15),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14ee06:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14ee09:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14ee0d:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14ee10:	0f 85 50 01 00 00    	jne    14ef66 <MultiSteersOdometer::CalSpeed()+0x18d6>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14ee16:	49 8b 07             	mov    (%r15),%rax
  14ee19:	4c 89 ff             	mov    %r15,%rdi
  14ee1c:	ff 50 18             	call   *0x18(%rax)
  14ee1f:	e9 42 01 00 00       	jmp    14ef66 <MultiSteersOdometer::CalSpeed()+0x18d6>
MultiSteersOdometer::CalSpeed():
  14ee24:	49 89 c6             	mov    %rax,%r14
  14ee27:	e9 48 01 00 00       	jmp    14ef74 <MultiSteersOdometer::CalSpeed()+0x18e4>
  14ee2c:	49 89 c6             	mov    %rax,%r14
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14ee2f:	4c 39 eb             	cmp    %r13,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14ee32:	0f 84 5b 01 00 00    	je     14ef93 <MultiSteersOdometer::CalSpeed()+0x1903>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14ee38:	48 89 df             	mov    %rbx,%rdi
  14ee3b:	e8 f0 5b f3 ff       	call   84a30 <operator delete(void*)@plt>
  14ee40:	e9 4e 01 00 00       	jmp    14ef93 <MultiSteersOdometer::CalSpeed()+0x1903>
MultiSteersOdometer::CalSpeed():
  14ee45:	49 89 c6             	mov    %rax,%r14
  14ee48:	e9 5a 01 00 00       	jmp    14efa7 <MultiSteersOdometer::CalSpeed()+0x1917>
  14ee4d:	49 89 c6             	mov    %rax,%r14
  14ee50:	e9 6c 01 00 00       	jmp    14efc1 <MultiSteersOdometer::CalSpeed()+0x1931>
  14ee55:	49 89 c6             	mov    %rax,%r14
  14ee58:	e9 64 01 00 00       	jmp    14efc1 <MultiSteersOdometer::CalSpeed()+0x1931>
  14ee5d:	49 89 c6             	mov    %rax,%r14
  14ee60:	e9 5c 01 00 00       	jmp    14efc1 <MultiSteersOdometer::CalSpeed()+0x1931>
  14ee65:	e9 ca 00 00 00       	jmp    14ef34 <MultiSteersOdometer::CalSpeed()+0x18a4>
  14ee6a:	49 89 c6             	mov    %rax,%r14
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:690
  14ee6d:	4d 85 ff             	test   %r15,%r15
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14ee70:	0f 84 82 02 00 00    	je     14f0f8 <MultiSteersOdometer::CalSpeed()+0x1a68>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14ee76:	48 83 3d 2a 8c 2b 00 	cmpq   $0x0,0x2b8c2a(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14ee7d:	00 
  14ee7e:	74 15                	je     14ee95 <MultiSteersOdometer::CalSpeed()+0x1805>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14ee80:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14ee85:	f0 41 0f c1 47 08    	lock xadd %eax,0x8(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14ee8b:	83 f8 01             	cmp    $0x1,%eax
  14ee8e:	74 19                	je     14eea9 <MultiSteersOdometer::CalSpeed()+0x1819>
  14ee90:	e9 63 02 00 00       	jmp    14f0f8 <MultiSteersOdometer::CalSpeed()+0x1a68>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14ee95:	41 8b 47 08          	mov    0x8(%r15),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14ee99:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14ee9c:	41 89 4f 08          	mov    %ecx,0x8(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14eea0:	83 f8 01             	cmp    $0x1,%eax
  14eea3:	0f 85 4f 02 00 00    	jne    14f0f8 <MultiSteersOdometer::CalSpeed()+0x1a68>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14eea9:	49 8b 07             	mov    (%r15),%rax
  14eeac:	4c 89 ff             	mov    %r15,%rdi
  14eeaf:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14eeb2:	48 83 3d ee 8b 2b 00 	cmpq   $0x0,0x2b8bee(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14eeb9:	00 
  14eeba:	74 15                	je     14eed1 <MultiSteersOdometer::CalSpeed()+0x1841>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14eebc:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14eec1:	f0 41 0f c1 47 0c    	lock xadd %eax,0xc(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14eec7:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14eeca:	74 19                	je     14eee5 <MultiSteersOdometer::CalSpeed()+0x1855>
  14eecc:	e9 27 02 00 00       	jmp    14f0f8 <MultiSteersOdometer::CalSpeed()+0x1a68>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14eed1:	41 8b 47 0c          	mov    0xc(%r15),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14eed5:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14eed8:	41 89 4f 0c          	mov    %ecx,0xc(%r15)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14eedc:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14eedf:	0f 85 13 02 00 00    	jne    14f0f8 <MultiSteersOdometer::CalSpeed()+0x1a68>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14eee5:	49 8b 07             	mov    (%r15),%rax
  14eee8:	4c 89 ff             	mov    %r15,%rdi
  14eeeb:	ff 50 18             	call   *0x18(%rax)
  14eeee:	e9 05 02 00 00       	jmp    14f0f8 <MultiSteersOdometer::CalSpeed()+0x1a68>
MultiSteersOdometer::CalSpeed():
  14eef3:	49 89 c6             	mov    %rax,%r14
  14eef6:	e9 0b 02 00 00       	jmp    14f106 <MultiSteersOdometer::CalSpeed()+0x1a76>
  14eefb:	49 89 c6             	mov    %rax,%r14
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14eefe:	4c 39 eb             	cmp    %r13,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14ef01:	0f 84 1e 02 00 00    	je     14f125 <MultiSteersOdometer::CalSpeed()+0x1a95>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14ef07:	48 89 df             	mov    %rbx,%rdi
  14ef0a:	e8 21 5b f3 ff       	call   84a30 <operator delete(void*)@plt>
  14ef0f:	e9 11 02 00 00       	jmp    14f125 <MultiSteersOdometer::CalSpeed()+0x1a95>
MultiSteersOdometer::CalSpeed():
  14ef14:	49 89 c6             	mov    %rax,%r14
  14ef17:	e9 18 02 00 00       	jmp    14f134 <MultiSteersOdometer::CalSpeed()+0x1aa4>
  14ef1c:	49 89 c6             	mov    %rax,%r14
  14ef1f:	e9 2a 02 00 00       	jmp    14f14e <MultiSteersOdometer::CalSpeed()+0x1abe>
  14ef24:	49 89 c6             	mov    %rax,%r14
  14ef27:	e9 22 02 00 00       	jmp    14f14e <MultiSteersOdometer::CalSpeed()+0x1abe>
  14ef2c:	49 89 c6             	mov    %rax,%r14
  14ef2f:	e9 1a 02 00 00       	jmp    14f14e <MultiSteersOdometer::CalSpeed()+0x1abe>
  14ef34:	49 89 c6             	mov    %rax,%r14
  14ef37:	e9 c2 02 00 00       	jmp    14f1fe <MultiSteersOdometer::CalSpeed()+0x1b6e>
  14ef3c:	49 89 c6             	mov    %rax,%r14
  14ef3f:	e9 a2 03 00 00       	jmp    14f2e6 <MultiSteersOdometer::CalSpeed()+0x1c56>
  14ef44:	49 89 c6             	mov    %rax,%r14
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14ef47:	48 8b 8c 24 00 01 00 	mov    0x100(%rsp),%rcx
  14ef4e:	00 
  14ef4f:	48 85 c9             	test   %rcx,%rcx
  14ef52:	74 12                	je     14ef66 <MultiSteersOdometer::CalSpeed()+0x18d6>
MultiSteersOdometer::CalSpeed():
  14ef54:	48 8d bc 24 f0 00 00 	lea    0xf0(%rsp),%rdi
  14ef5b:	00 
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14ef5c:	ba 03 00 00 00       	mov    $0x3,%edx
  14ef61:	48 89 fe             	mov    %rdi,%rsi
  14ef64:	ff d1                	call   *%rcx
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14ef66:	48 8b 5c 24 68       	mov    0x68(%rsp),%rbx
  14ef6b:	48 85 db             	test   %rbx,%rbx
  14ef6e:	0f 85 db 00 00 00    	jne    14f04f <MultiSteersOdometer::CalSpeed()+0x19bf>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14ef74:	48 8b 8c 24 c0 00 00 	mov    0xc0(%rsp),%rcx
  14ef7b:	00 
  14ef7c:	48 85 c9             	test   %rcx,%rcx
  14ef7f:	74 12                	je     14ef93 <MultiSteersOdometer::CalSpeed()+0x1903>
MultiSteersOdometer::CalSpeed():
  14ef81:	48 8d bc 24 b0 00 00 	lea    0xb0(%rsp),%rdi
  14ef88:	00 
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14ef89:	ba 03 00 00 00       	mov    $0x3,%edx
  14ef8e:	48 89 fe             	mov    %rdi,%rsi
  14ef91:	ff d1                	call   *%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14ef93:	48 8b 7c 24 40       	mov    0x40(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14ef98:	48 8d 44 24 50       	lea    0x50(%rsp),%rax
  14ef9d:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14efa0:	74 05                	je     14efa7 <MultiSteersOdometer::CalSpeed()+0x1917>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14efa2:	e8 89 5a f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14efa7:	48 8b bc 24 20 01 00 	mov    0x120(%rsp),%rdi
  14efae:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14efaf:	48 8d 84 24 30 01 00 	lea    0x130(%rsp),%rax
  14efb6:	00 
  14efb7:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14efba:	74 05                	je     14efc1 <MultiSteersOdometer::CalSpeed()+0x1931>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14efbc:	e8 6f 5a f3 ff       	call   84a30 <operator delete(void*)@plt>
MultiSteersOdometer::CalSpeed():
  14efc1:	48 8b 84 24 90 00 00 	mov    0x90(%rsp),%rax
  14efc8:	00 
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::~basic_stringstream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:731
  14efc9:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  14efd0:	00 
  14efd1:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14efd5:	48 8b 8c 24 88 00 00 	mov    0x88(%rsp),%rcx
  14efdc:	00 
  14efdd:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  14efe4:	00 
  14efe5:	48 8b 84 24 e8 00 00 	mov    0xe8(%rsp),%rax
  14efec:	00 
  14efed:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  14eff4:	00 
std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::~basic_stringbuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/sstream.tcc:291
  14eff5:	4c 89 a4 24 58 01 00 	mov    %r12,0x158(%rsp)
  14effc:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14effd:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  14f004:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14f005:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  14f00c:	00 
  14f00d:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14f010:	74 05                	je     14f017 <MultiSteersOdometer::CalSpeed()+0x1987>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14f012:	e8 19 5a f3 ff       	call   84a30 <operator delete(void*)@plt>
std::basic_streambuf<char, std::char_traits<char> >::~basic_streambuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/streambuf:198
  14f017:	48 8b 84 24 98 00 00 	mov    0x98(%rsp),%rax
  14f01e:	00 
  14f01f:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  14f026:	00 
  14f027:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  14f02e:	00 
  14f02f:	e8 fc 71 f3 ff       	call   86230 <std::locale::~locale()@plt>
  14f034:	48 8b 44 24 08       	mov    0x8(%rsp),%rax
std::basic_istream<char, std::char_traits<char> >::~basic_istream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/istream:104
  14f039:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  14f040:	00 
  14f041:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14f045:	48 8b 4c 24 38       	mov    0x38(%rsp),%rcx
  14f04a:	e9 8e 01 00 00       	jmp    14f1dd <MultiSteersOdometer::CalSpeed()+0x1b4d>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14f04f:	48 83 3d 51 8a 2b 00 	cmpq   $0x0,0x2b8a51(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14f056:	00 
  14f057:	74 14                	je     14f06d <MultiSteersOdometer::CalSpeed()+0x19dd>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14f059:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14f05e:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14f063:	83 f8 01             	cmp    $0x1,%eax
  14f066:	74 17                	je     14f07f <MultiSteersOdometer::CalSpeed()+0x19ef>
  14f068:	e9 07 ff ff ff       	jmp    14ef74 <MultiSteersOdometer::CalSpeed()+0x18e4>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14f06d:	8b 43 08             	mov    0x8(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14f070:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14f073:	89 4b 08             	mov    %ecx,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14f076:	83 f8 01             	cmp    $0x1,%eax
  14f079:	0f 85 f5 fe ff ff    	jne    14ef74 <MultiSteersOdometer::CalSpeed()+0x18e4>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14f07f:	48 8b 03             	mov    (%rbx),%rax
  14f082:	48 89 df             	mov    %rbx,%rdi
  14f085:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14f088:	48 83 3d 18 8a 2b 00 	cmpq   $0x0,0x2b8a18(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14f08f:	00 
  14f090:	74 14                	je     14f0a6 <MultiSteersOdometer::CalSpeed()+0x1a16>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14f092:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14f097:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14f09c:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14f09f:	74 17                	je     14f0b8 <MultiSteersOdometer::CalSpeed()+0x1a28>
  14f0a1:	e9 ce fe ff ff       	jmp    14ef74 <MultiSteersOdometer::CalSpeed()+0x18e4>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14f0a6:	8b 43 0c             	mov    0xc(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14f0a9:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14f0ac:	89 4b 0c             	mov    %ecx,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14f0af:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14f0b2:	0f 85 bc fe ff ff    	jne    14ef74 <MultiSteersOdometer::CalSpeed()+0x18e4>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14f0b8:	48 8b 03             	mov    (%rbx),%rax
  14f0bb:	48 89 df             	mov    %rbx,%rdi
  14f0be:	ff 50 18             	call   *0x18(%rax)
  14f0c1:	e9 ae fe ff ff       	jmp    14ef74 <MultiSteersOdometer::CalSpeed()+0x18e4>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14f0c6:	48 89 c7             	mov    %rax,%rdi
  14f0c9:	e8 d2 7c f5 ff       	call   a6da0 <__clang_call_terminate>
  14f0ce:	48 89 c7             	mov    %rax,%rdi
  14f0d1:	e8 ca 7c f5 ff       	call   a6da0 <__clang_call_terminate>
MultiSteersOdometer::CalSpeed():
  14f0d6:	49 89 c6             	mov    %rax,%r14
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14f0d9:	48 8b 8c 24 00 01 00 	mov    0x100(%rsp),%rcx
  14f0e0:	00 
  14f0e1:	48 85 c9             	test   %rcx,%rcx
  14f0e4:	74 12                	je     14f0f8 <MultiSteersOdometer::CalSpeed()+0x1a68>
MultiSteersOdometer::CalSpeed():
  14f0e6:	48 8d bc 24 f0 00 00 	lea    0xf0(%rsp),%rdi
  14f0ed:	00 
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14f0ee:	ba 03 00 00 00       	mov    $0x3,%edx
  14f0f3:	48 89 fe             	mov    %rdi,%rsi
  14f0f6:	ff d1                	call   *%rcx
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14f0f8:	48 8b 5c 24 68       	mov    0x68(%rsp),%rbx
  14f0fd:	48 85 db             	test   %rbx,%rbx
  14f100:	0f 85 17 01 00 00    	jne    14f21d <MultiSteersOdometer::CalSpeed()+0x1b8d>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14f106:	48 8b 8c 24 c0 00 00 	mov    0xc0(%rsp),%rcx
  14f10d:	00 
  14f10e:	48 85 c9             	test   %rcx,%rcx
  14f111:	74 12                	je     14f125 <MultiSteersOdometer::CalSpeed()+0x1a95>
MultiSteersOdometer::CalSpeed():
  14f113:	48 8d bc 24 b0 00 00 	lea    0xb0(%rsp),%rdi
  14f11a:	00 
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14f11b:	ba 03 00 00 00       	mov    $0x3,%edx
  14f120:	48 89 fe             	mov    %rdi,%rsi
  14f123:	ff d1                	call   *%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f125:	48 8b 7c 24 40       	mov    0x40(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14f12a:	4c 39 e7             	cmp    %r12,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14f12d:	74 05                	je     14f134 <MultiSteersOdometer::CalSpeed()+0x1aa4>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14f12f:	e8 fc 58 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f134:	48 8b bc 24 20 01 00 	mov    0x120(%rsp),%rdi
  14f13b:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14f13c:	48 8d 84 24 30 01 00 	lea    0x130(%rsp),%rax
  14f143:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14f144:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14f147:	74 05                	je     14f14e <MultiSteersOdometer::CalSpeed()+0x1abe>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14f149:	e8 e2 58 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::~basic_stringstream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:731
  14f14e:	48 8b 1d 13 89 2b 00 	mov    0x2b8913(%rip),%rbx        # 407a68 <VTT for std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  14f155:	48 8b 03             	mov    (%rbx),%rax
  14f158:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  14f15f:	00 
  14f160:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  14f164:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14f168:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  14f16f:	00 
  14f170:	48 8b 43 48          	mov    0x48(%rbx),%rax
  14f174:	48 89 84 24 50 01 00 	mov    %rax,0x150(%rsp)
  14f17b:	00 
std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::~basic_stringbuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/sstream.tcc:291
  14f17c:	48 8b 05 e5 7c 2b 00 	mov    0x2b7ce5(%rip),%rax        # 406e68 <vtable for std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  14f183:	48 83 c0 10          	add    $0x10,%rax
  14f187:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  14f18e:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f18f:	48 8b bc 24 a0 01 00 	mov    0x1a0(%rsp),%rdi
  14f196:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14f197:	48 8d 84 24 b0 01 00 	lea    0x1b0(%rsp),%rax
  14f19e:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14f19f:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14f1a2:	74 05                	je     14f1a9 <MultiSteersOdometer::CalSpeed()+0x1b19>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14f1a4:	e8 87 58 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::basic_streambuf<char, std::char_traits<char> >::~basic_streambuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/streambuf:198
  14f1a9:	48 8b 05 68 87 2b 00 	mov    0x2b8768(%rip),%rax        # 407918 <vtable for std::basic_streambuf<char, std::char_traits<char> >@GLIBCXX_3.4>
  14f1b0:	48 83 c0 10          	add    $0x10,%rax
  14f1b4:	48 89 84 24 58 01 00 	mov    %rax,0x158(%rsp)
  14f1bb:	00 
  14f1bc:	48 8d bc 24 90 01 00 	lea    0x190(%rsp),%rdi
  14f1c3:	00 
  14f1c4:	e8 67 70 f3 ff       	call   86230 <std::locale::~locale()@plt>
std::basic_istream<char, std::char_traits<char> >::~basic_istream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/istream:104
  14f1c9:	48 8b 43 10          	mov    0x10(%rbx),%rax
  14f1cd:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  14f1d1:	48 89 84 24 40 01 00 	mov    %rax,0x140(%rsp)
  14f1d8:	00 
  14f1d9:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14f1dd:	48 89 8c 04 40 01 00 	mov    %rcx,0x140(%rsp,%rax,1)
  14f1e4:	00 
  14f1e5:	48 c7 84 24 48 01 00 	movq   $0x0,0x148(%rsp)
  14f1ec:	00 00 00 00 00 
std::basic_ios<char, std::char_traits<char> >::~basic_ios():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:282
  14f1f1:	48 8d bc 24 c0 01 00 	lea    0x1c0(%rsp),%rdi
  14f1f8:	00 
  14f1f9:	e8 22 61 f3 ff       	call   85320 <std::ios_base::~ios_base()@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::~DenseStorage():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:542
  14f1fe:	48 8b bc 24 10 01 00 	mov    0x110(%rsp),%rdi
  14f205:	00 
Eigen::internal::aligned_free(void*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:177
  14f206:	e8 65 45 f3 ff       	call   83770 <free@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::~DenseStorage():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:542
  14f20b:	48 8b bc 24 a0 00 00 	mov    0xa0(%rsp),%rdi
  14f212:	00 
Eigen::internal::aligned_free(void*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:177
  14f213:	e8 58 45 f3 ff       	call   83770 <free@plt>
MultiSteersOdometer::CalSpeed():
  14f218:	e9 c9 00 00 00       	jmp    14f2e6 <MultiSteersOdometer::CalSpeed()+0x1c56>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14f21d:	48 83 3d 83 88 2b 00 	cmpq   $0x0,0x2b8883(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14f224:	00 
  14f225:	74 14                	je     14f23b <MultiSteersOdometer::CalSpeed()+0x1bab>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14f227:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14f22c:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14f231:	83 f8 01             	cmp    $0x1,%eax
  14f234:	74 17                	je     14f24d <MultiSteersOdometer::CalSpeed()+0x1bbd>
  14f236:	e9 cb fe ff ff       	jmp    14f106 <MultiSteersOdometer::CalSpeed()+0x1a76>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14f23b:	8b 43 08             	mov    0x8(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14f23e:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14f241:	89 4b 08             	mov    %ecx,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14f244:	83 f8 01             	cmp    $0x1,%eax
  14f247:	0f 85 b9 fe ff ff    	jne    14f106 <MultiSteersOdometer::CalSpeed()+0x1a76>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14f24d:	48 8b 03             	mov    (%rbx),%rax
  14f250:	48 89 df             	mov    %rbx,%rdi
  14f253:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14f256:	48 83 3d 4a 88 2b 00 	cmpq   $0x0,0x2b884a(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14f25d:	00 
  14f25e:	74 14                	je     14f274 <MultiSteersOdometer::CalSpeed()+0x1be4>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14f260:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14f265:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14f26a:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14f26d:	74 17                	je     14f286 <MultiSteersOdometer::CalSpeed()+0x1bf6>
  14f26f:	e9 92 fe ff ff       	jmp    14f106 <MultiSteersOdometer::CalSpeed()+0x1a76>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14f274:	8b 43 0c             	mov    0xc(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14f277:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14f27a:	89 4b 0c             	mov    %ecx,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14f27d:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14f280:	0f 85 80 fe ff ff    	jne    14f106 <MultiSteersOdometer::CalSpeed()+0x1a76>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14f286:	48 8b 03             	mov    (%rbx),%rax
  14f289:	48 89 df             	mov    %rbx,%rdi
  14f28c:	ff 50 18             	call   *0x18(%rax)
  14f28f:	e9 72 fe ff ff       	jmp    14f106 <MultiSteersOdometer::CalSpeed()+0x1a76>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14f294:	48 89 c7             	mov    %rax,%rdi
  14f297:	e8 04 7b f5 ff       	call   a6da0 <__clang_call_terminate>
  14f29c:	48 89 c7             	mov    %rax,%rdi
  14f29f:	e8 fc 7a f5 ff       	call   a6da0 <__clang_call_terminate>
MultiSteersOdometer::CalSpeed():
  14f2a4:	49 89 c6             	mov    %rax,%r14
  14f2a7:	e9 5f ff ff ff       	jmp    14f20b <MultiSteersOdometer::CalSpeed()+0x1b7b>
  14f2ac:	49 89 c6             	mov    %rax,%r14
  14f2af:	eb 35                	jmp    14f2e6 <MultiSteersOdometer::CalSpeed()+0x1c56>
  14f2b1:	49 89 c6             	mov    %rax,%r14
  14f2b4:	eb 1e                	jmp    14f2d4 <MultiSteersOdometer::CalSpeed()+0x1c44>
  14f2b6:	49 89 c6             	mov    %rax,%r14
  14f2b9:	eb 2b                	jmp    14f2e6 <MultiSteersOdometer::CalSpeed()+0x1c56>
  14f2bb:	eb 00                	jmp    14f2bd <MultiSteersOdometer::CalSpeed()+0x1c2d>
  14f2bd:	49 89 c6             	mov    %rax,%r14
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f2c0:	48 8b 7c 24 10       	mov    0x10(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14f2c5:	48 8d 44 24 20       	lea    0x20(%rsp),%rax
  14f2ca:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14f2cd:	74 05                	je     14f2d4 <MultiSteersOdometer::CalSpeed()+0x1c44>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14f2cf:	e8 5c 57 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14f2d4:	48 8b bc 24 40 01 00 	mov    0x140(%rsp),%rdi
  14f2db:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14f2dc:	4c 39 e7             	cmp    %r12,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14f2df:	74 05                	je     14f2e6 <MultiSteersOdometer::CalSpeed()+0x1c56>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14f2e1:	e8 4a 57 f3 ff       	call   84a30 <operator delete(void*)@plt>
Eigen::DenseStorage<double, -1, -1, 1, 0>::~DenseStorage():
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:542
  14f2e6:	48 8b 7c 24 70       	mov    0x70(%rsp),%rdi
Eigen::internal::aligned_free(void*):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/util/Memory.h:177
  14f2eb:	e8 80 44 f3 ff       	call   83770 <free@plt>
MultiSteersOdometer::CalSpeed():
  14f2f0:	4c 89 f7             	mov    %r14,%rdi
  14f2f3:	e8 88 5c f3 ff       	call   84f80 <_Unwind_Resume@plt>
  14f2f8:	0f 1f 84 00 00 00 00 	nopl   0x0(%rax,%rax,1)
  14f2ff:	00 
