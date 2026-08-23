
/media/amap/6ab6980d-f090-4387-8753-a2251e75651d/usr/local/SeerRobotics/rbk/plugins/libOdoCalculator.so:     file format elf64-x86-64


Disassembly of section .text:

000000000014c9f0 <MultiSteersOdometer::CalOdoCoef()>:
MultiSteersOdometer::CalOdoCoef():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:79
  14c9f0:	55                   	push   %rbp
  14c9f1:	48 89 e5             	mov    %rsp,%rbp
  14c9f4:	41 57                	push   %r15
  14c9f6:	41 56                	push   %r14
  14c9f8:	41 55                	push   %r13
  14c9fa:	41 54                	push   %r12
  14c9fc:	53                   	push   %rbx
  14c9fd:	48 83 e4 f0          	and    $0xfffffffffffffff0,%rsp
  14ca01:	48 81 ec 00 03 00 00 	sub    $0x300,%rsp
  14ca08:	48 89 fb             	mov    %rdi,%rbx
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:81
  14ca0b:	e8 80 75 f3 ff       	call   83f90 <AbstractOdometer::CalOdoCoef()@plt>
  14ca10:	84 c0                	test   %al,%al
  14ca12:	74 35                	je     14ca49 <MultiSteersOdometer::CalOdoCoef()+0x59>
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:82
  14ca14:	c6 43 0a 00          	movb   $0x0,0xa(%rbx)
std::_Rb_tree<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::_Select1st<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > >::size() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:997
  14ca18:	48 8b b3 70 01 00 00 	mov    0x170(%rbx),%rsi
MultiSteersOdometer::CalOdoCoef():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:84
  14ca1f:	48 01 f6             	add    %rsi,%rsi
  14ca22:	4c 8d b3 78 01 00 00 	lea    0x178(%rbx),%r14
void Eigen::internal::resize_if_allowed<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, -1, 0, -1, -1> >, double, double>(Eigen::Matrix<double, -1, -1, 0, -1, -1>&, Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, -1, 0, -1, -1> > const&, Eigen::internal::assign_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:719
  14ca29:	48 39 b3 80 01 00 00 	cmp    %rsi,0x180(%rbx)
  14ca30:	48 89 5c 24 08       	mov    %rbx,0x8(%rsp)
  14ca35:	75 19                	jne    14ca50 <MultiSteersOdometer::CalOdoCoef()+0x60>
  14ca37:	48 83 bb 88 01 00 00 	cmpq   $0x3,0x188(%rbx)
  14ca3e:	03 
  14ca3f:	75 0f                	jne    14ca50 <MultiSteersOdometer::CalOdoCoef()+0x60>
MultiSteersOdometer::CalOdoCoef():
  14ca41:	41 bf 03 00 00 00    	mov    $0x3,%r15d
  14ca47:	eb 22                	jmp    14ca6b <MultiSteersOdometer::CalOdoCoef()+0x7b>
  14ca49:	31 c0                	xor    %eax,%eax
  14ca4b:	e9 13 09 00 00       	jmp    14d363 <MultiSteersOdometer::CalOdoCoef()+0x973>
void Eigen::internal::resize_if_allowed<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, -1, 0, -1, -1> >, double, double>(Eigen::Matrix<double, -1, -1, 0, -1, -1>&, Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, -1, 0, -1, -1> > const&, Eigen::internal::assign_op<double, double> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:720
  14ca50:	ba 03 00 00 00       	mov    $0x3,%edx
  14ca55:	4c 89 f7             	mov    %r14,%rdi
  14ca58:	e8 53 88 f3 ff       	call   852b0 <Eigen::PlainObjectBase<Eigen::Matrix<double, -1, -1, 0, -1, -1> >::resize(long, long)@plt>
Eigen::DenseStorage<double, -1, -1, -1, 0>::rows() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:394
  14ca5d:	48 8b b3 80 01 00 00 	mov    0x180(%rbx),%rsi
Eigen::DenseStorage<double, -1, -1, -1, 0>::cols() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:395
  14ca64:	4c 8b bb 88 01 00 00 	mov    0x188(%rbx),%r15
Eigen::EigenBase<Eigen::Matrix<double, -1, -1, 0, -1, -1> >::size() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/EigenBase.h:66
  14ca6b:	4c 0f af fe          	imul   %rsi,%r15
MultiSteersOdometer::CalOdoCoef():
  14ca6f:	4c 89 74 24 38       	mov    %r14,0x38(%rsp)
Eigen::DenseStorage<double, -1, -1, -1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:416
  14ca74:	4d 8b 36             	mov    (%r14),%r14
Eigen::internal::dense_assignment_loop<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, -1, 0, -1, -1> > >, Eigen::internal::assign_op<double, double>, 0>, 3, 0>::run(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, -1, 0, -1, -1> > >, Eigen::internal::assign_op<double, double>, 0>&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:411
  14ca77:	4c 89 fb             	mov    %r15,%rbx
  14ca7a:	48 c1 eb 3f          	shr    $0x3f,%rbx
  14ca7e:	4c 01 fb             	add    %r15,%rbx
  14ca81:	49 89 dc             	mov    %rbx,%r12
  14ca84:	49 83 e4 fe          	and    $0xfffffffffffffffe,%r12
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:415
  14ca88:	49 83 ff 02          	cmp    $0x2,%r15
  14ca8c:	7c 27                	jl     14cab5 <MultiSteersOdometer::CalOdoCoef()+0xc5>
  14ca8e:	49 83 fc 01          	cmp    $0x1,%r12
  14ca92:	b8 02 00 00 00       	mov    $0x2,%eax
  14ca97:	49 0f 4f c4          	cmovg  %r12,%rax
  14ca9b:	48 8d 14 c5 f8 ff ff 	lea    -0x8(,%rax,8),%rdx
  14caa2:	ff 
  14caa3:	48 83 e2 f0          	and    $0xfffffffffffffff0,%rdx
  14caa7:	48 83 c2 10          	add    $0x10,%rdx
void Eigen::internal::pstore<double, double __vector(2)>(double*, double __vector(2) const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/arch/SSE/PacketMath.h:359
  14caab:	31 f6                	xor    %esi,%esi
  14caad:	4c 89 f7             	mov    %r14,%rdi
  14cab0:	e8 cb 73 f3 ff       	call   83e80 <memset@plt>
MultiSteersOdometer::CalOdoCoef():
  14cab5:	48 8b 44 24 08       	mov    0x8(%rsp),%rax
  14caba:	4c 8d a8 48 01 00 00 	lea    0x148(%rax),%r13
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, -1, 0, -1, -1> > >, Eigen::internal::assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, -1, 0, -1, -1> > >, Eigen::internal::assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14cac1:	4d 39 fc             	cmp    %r15,%r12
  14cac4:	7d 1c                	jge    14cae2 <MultiSteersOdometer::CalOdoCoef()+0xf2>
MultiSteersOdometer::CalOdoCoef():
  14cac6:	48 d1 fb             	sar    %rbx
void Eigen::internal::unaligned_dense_assignment_loop<false>::run<Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, -1, 0, -1, -1> > >, Eigen::internal::assign_op<double, double>, 0> >(Eigen::internal::generic_dense_assignment_kernel<Eigen::internal::evaluator<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, Eigen::internal::evaluator<Eigen::CwiseNullaryOp<Eigen::internal::scalar_constant_op<double>, Eigen::Matrix<double, -1, -1, 0, -1, -1> > >, Eigen::internal::assign_op<double, double>, 0>&, long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:389
  14cac9:	4b 8d 3c e6          	lea    (%r14,%r12,8),%rdi
  14cacd:	49 c1 e7 03          	shl    $0x3,%r15
  14cad1:	48 c1 e3 04          	shl    $0x4,%rbx
  14cad5:	49 29 df             	sub    %rbx,%r15
Eigen::internal::assign_op<double, double>::assignCoeff(double&, double const&) const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/functors/AssignmentFunctors.h:24
  14cad8:	31 f6                	xor    %esi,%esi
  14cada:	4c 89 fa             	mov    %r15,%rdx
  14cadd:	e8 9e 73 f3 ff       	call   83e80 <memset@plt>
std::_Rb_tree<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::_Select1st<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > >::begin():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:961
  14cae2:	49 8b 4d 18          	mov    0x18(%r13),%rcx
std::_Rb_tree<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::_Select1st<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > >::end():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:969
  14cae6:	49 83 c5 08          	add    $0x8,%r13
  14caea:	4c 89 ac 24 b0 00 00 	mov    %r13,0xb0(%rsp)
  14caf1:	00 
std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >::operator!=(std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:320
  14caf2:	4c 39 e9             	cmp    %r13,%rcx
  14caf5:	48 8b 5c 24 08       	mov    0x8(%rsp),%rbx
MultiSteersOdometer::CalOdoCoef():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:86
  14cafa:	0f 84 cb 01 00 00    	je     14cccb <MultiSteersOdometer::CalOdoCoef()+0x2db>
  14cb00:	4c 8d 73 10          	lea    0x10(%rbx),%r14
  14cb04:	41 bd 01 00 00 00    	mov    $0x1,%r13d
  14cb0a:	4c 8d a4 24 f8 00 00 	lea    0xf8(%rsp),%r12
  14cb11:	00 
  14cb12:	49 b8 00 00 00 00 00 	movabs $0x3ff0000000000000,%r8
  14cb19:	00 f0 3f 
  14cb1c:	4c 89 b4 24 b8 00 00 	mov    %r14,0xb8(%rsp)
  14cb23:	00 
  14cb24:	66 66 66 2e 0f 1f 84 	data16 data16 cs nopw 0x0(%rax,%rax,1)
  14cb2b:	00 00 00 00 00 
  14cb30:	4c 89 e3             	mov    %r12,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14cb33:	48 8d 84 24 08 01 00 	lea    0x108(%rsp),%rax
  14cb3a:	00 
  14cb3b:	48 89 84 24 f8 00 00 	mov    %rax,0xf8(%rsp)
  14cb42:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14cb43:	4c 8b 71 20          	mov    0x20(%rcx),%r14
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14cb47:	4c 8b 61 28          	mov    0x28(%rcx),%r12
bool __gnu_cxx::__is_null_pointer<char>(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/type_traits.h:153
  14cb4b:	4d 85 f6             	test   %r14,%r14
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:211
  14cb4e:	75 09                	jne    14cb59 <MultiSteersOdometer::CalOdoCoef()+0x169>
  14cb50:	4d 85 e4             	test   %r12,%r12
  14cb53:	0f 85 19 08 00 00    	jne    14d372 <MultiSteersOdometer::CalOdoCoef()+0x982>
MultiSteersOdometer::CalOdoCoef():
  14cb59:	48 89 8c 24 c0 00 00 	mov    %rcx,0xc0(%rsp)
  14cb60:	00 
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:215
  14cb61:	4c 89 64 24 10       	mov    %r12,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14cb66:	48 8d 84 24 08 01 00 	lea    0x108(%rsp),%rax
  14cb6d:	00 
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:217
  14cb6e:	49 83 fc 10          	cmp    $0x10,%r12
  14cb72:	72 2e                	jb     14cba2 <MultiSteersOdometer::CalOdoCoef()+0x1b2>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:219
  14cb74:	31 d2                	xor    %edx,%edx
  14cb76:	48 89 df             	mov    %rbx,%rdi
  14cb79:	48 8d 74 24 10       	lea    0x10(%rsp),%rsi
  14cb7e:	e8 ad 85 f3 ff       	call   85130 <std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_create(unsigned long&, unsigned long)@plt>
  14cb83:	49 b8 00 00 00 00 00 	movabs $0x3ff0000000000000,%r8
  14cb8a:	00 f0 3f 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14cb8d:	48 89 84 24 f8 00 00 	mov    %rax,0xf8(%rsp)
  14cb94:	00 
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:220
  14cb95:	48 8b 4c 24 10       	mov    0x10(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14cb9a:	48 89 8c 24 08 01 00 	mov    %rcx,0x108(%rsp)
  14cba1:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  14cba2:	4d 85 e4             	test   %r12,%r12
  14cba5:	74 31                	je     14cbd8 <MultiSteersOdometer::CalOdoCoef()+0x1e8>
  14cba7:	49 83 fc 01          	cmp    $0x1,%r12
  14cbab:	75 13                	jne    14cbc0 <MultiSteersOdometer::CalOdoCoef()+0x1d0>
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14cbad:	41 0f b6 0e          	movzbl (%r14),%ecx
  14cbb1:	88 08                	mov    %cl,(%rax)
  14cbb3:	eb 23                	jmp    14cbd8 <MultiSteersOdometer::CalOdoCoef()+0x1e8>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14cbb5:	66 66 2e 0f 1f 84 00 	data16 cs nopw 0x0(%rax,%rax,1)
  14cbbc:	00 00 00 00 
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14cbc0:	48 89 c7             	mov    %rax,%rdi
  14cbc3:	4c 89 f6             	mov    %r14,%rsi
  14cbc6:	4c 89 e2             	mov    %r12,%rdx
  14cbc9:	e8 a2 68 f3 ff       	call   83470 <memcpy@plt>
  14cbce:	49 b8 00 00 00 00 00 	movabs $0x3ff0000000000000,%r8
  14cbd5:	00 f0 3f 
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:232
  14cbd8:	48 8b 44 24 10       	mov    0x10(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14cbdd:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  14cbe4:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14cbe5:	48 8b 8c 24 f8 00 00 	mov    0xf8(%rsp),%rcx
  14cbec:	00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14cbed:	c6 04 01 00          	movb   $0x0,(%rcx,%rax,1)
Eigen::DenseStorage<double, -1, -1, -1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:416
  14cbf1:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
  14cbf6:	48 8b 00             	mov    (%rax),%rax
MultiSteersOdometer::CalOdoCoef():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:88
  14cbf9:	4e 89 44 e8 f8       	mov    %r8,-0x8(%rax,%r13,8)
  14cbfe:	4c 8b b4 24 b8 00 00 	mov    0xb8(%rsp),%r14
  14cc05:	00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:89
  14cc06:	4c 89 f7             	mov    %r14,%rdi
  14cc09:	49 89 dc             	mov    %rbx,%r12
  14cc0c:	4c 89 e6             	mov    %r12,%rsi
  14cc0f:	4d 89 c7             	mov    %r8,%r15
  14cc12:	e8 19 92 f3 ff       	call   85e30 <std::map<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, MotorParam, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, MotorParam> > >::operator[](std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&)@plt>
  14cc17:	48 8b 5c 24 08       	mov    0x8(%rsp),%rbx
MotorParam::ySum():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/odocalculatorstructs.h:38
  14cc1c:	f2 0f 10 40 28       	movsd  0x28(%rax),%xmm0
  14cc21:	f2 0f 58 80 98 00 00 	addsd  0x98(%rax),%xmm0
  14cc28:	00 
Eigen::DenseStorage<double, -1, -1, -1, 0>::data() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:416
  14cc29:	48 8b 83 78 01 00 00 	mov    0x178(%rbx),%rax
Eigen::DenseStorage<double, -1, -1, -1, 0>::rows() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:394
  14cc30:	48 8b 8b 80 01 00 00 	mov    0x180(%rbx),%rcx
Eigen::internal::evaluator<Eigen::PlainObjectBase<Eigen::Matrix<double, -1, -1, 0, -1, -1> > >::coeffRef(long, long):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/CoreEvaluators.h:181
  14cc37:	4a 8d 14 29          	lea    (%rcx,%r13,1),%rdx
MultiSteersOdometer::CalOdoCoef():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:89
  14cc3b:	48 c1 e1 04          	shl    $0x4,%rcx
  14cc3f:	48 01 c1             	add    %rax,%rcx
  14cc42:	66 0f 57 05 a6 1e 05 	xorpd  0x51ea6(%rip),%xmm0        # 19eaf0 <typeinfo name for rbk::Logger::Thread::move2thread<AckermanOdometer::CaldPose()::$_2>(AckermanOdometer::CaldPose()::$_2&&)::{lambda()#1}+0x190>
  14cc49:	00 
  14cc4a:	66 42 0f 13 44 e9 f8 	movlpd %xmm0,-0x8(%rcx,%r13,8)
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:90
  14cc51:	4c 89 3c d0          	mov    %r15,(%rax,%rdx,8)
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:91
  14cc55:	4c 89 f7             	mov    %r14,%rdi
  14cc58:	4c 89 e6             	mov    %r12,%rsi
  14cc5b:	e8 d0 91 f3 ff       	call   85e30 <std::map<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, MotorParam, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, MotorParam> > >::operator[](std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&)@plt>
MotorParam::xSum():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/odocalculatorstructs.h:37
  14cc60:	f2 0f 10 40 20       	movsd  0x20(%rax),%xmm0
  14cc65:	f2 0f 58 80 90 00 00 	addsd  0x90(%rax),%xmm0
  14cc6c:	00 
Eigen::DenseStorage<double, -1, -1, -1, 0>::rows() const:
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/DenseStorage.h:394
  14cc6d:	48 8b 83 80 01 00 00 	mov    0x180(%rbx),%rax
MultiSteersOdometer::CalOdoCoef():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:91
  14cc74:	48 c1 e0 04          	shl    $0x4,%rax
  14cc78:	48 03 83 78 01 00 00 	add    0x178(%rbx),%rax
  14cc7f:	f2 42 0f 11 04 e8    	movsd  %xmm0,(%rax,%r13,8)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14cc85:	48 8b bc 24 f8 00 00 	mov    0xf8(%rsp),%rdi
  14cc8c:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14cc8d:	48 8d 84 24 08 01 00 	lea    0x108(%rsp),%rax
  14cc94:	00 
  14cc95:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14cc98:	74 05                	je     14cc9f <MultiSteersOdometer::CalOdoCoef()+0x2af>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14cc9a:	e8 91 7d f3 ff       	call   84a30 <operator delete(void*)@plt>
std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >::operator++(int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:295
  14cc9f:	48 8b bc 24 c0 00 00 	mov    0xc0(%rsp),%rdi
  14cca6:	00 
  14cca7:	e8 74 94 f3 ff       	call   86120 <std::_Rb_tree_increment(std::_Rb_tree_node_base*)@plt>
  14ccac:	48 89 c1             	mov    %rax,%rcx
MultiSteersOdometer::CalOdoCoef():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:86
  14ccaf:	49 83 c5 02          	add    $0x2,%r13
std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >::operator!=(std::_Rb_tree_iterator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/stl_tree.h:320
  14ccb3:	48 3b 8c 24 b0 00 00 	cmp    0xb0(%rsp),%rcx
  14ccba:	00 
  14ccbb:	49 b8 00 00 00 00 00 	movabs $0x3ff0000000000000,%r8
  14ccc2:	00 f0 3f 
MultiSteersOdometer::CalOdoCoef():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:86
  14ccc5:	0f 85 65 fe ff ff    	jne    14cb30 <MultiSteersOdometer::CalOdoCoef()+0x140>
  14cccb:	48 8b 44 24 38       	mov    0x38(%rsp),%rax
Eigen::Product<Eigen::Inverse<Eigen::Product<Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, Eigen::Matrix<double, -1, -1, 0, -1, -1>, 0> >, Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, 0>::Product(Eigen::Inverse<Eigen::Product<Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, Eigen::Matrix<double, -1, -1, 0, -1, -1>, 0> > const&, Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> > const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/Product.h:93
  14ccd0:	48 89 84 24 f8 00 00 	mov    %rax,0xf8(%rsp)
  14ccd7:	00 
  14ccd8:	48 89 84 24 00 01 00 	mov    %rax,0x100(%rsp)
  14ccdf:	00 
  14cce0:	48 89 84 24 08 01 00 	mov    %rax,0x108(%rsp)
  14cce7:	00 
MultiSteersOdometer::CalOdoCoef():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:94
  14cce8:	48 8d bb 90 01 00 00 	lea    0x190(%rbx),%rdi
  14ccef:	48 8d b4 24 f8 00 00 	lea    0xf8(%rsp),%rsi
  14ccf6:	00 
  14ccf7:	48 8d 54 24 10       	lea    0x10(%rsp),%rdx
void Eigen::internal::call_assignment<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Product<Eigen::Inverse<Eigen::Product<Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, Eigen::Matrix<double, -1, -1, 0, -1, -1>, 0> >, Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, 0> >(Eigen::Matrix<double, -1, -1, 0, -1, -1>&, Eigen::Product<Eigen::Inverse<Eigen::Product<Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, Eigen::Matrix<double, -1, -1, 0, -1, -1>, 0> >, Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, 0> const&):
/root/.conan/data/eigen/3.3.9/x86_64/mno-avx/package/5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9/include/eigen3/Eigen/src/Core/AssignEvaluator.h:782
  14ccfc:	31 c9                	xor    %ecx,%ecx
  14ccfe:	e8 4d 65 f3 ff       	call   83250 <void Eigen::internal::call_assignment<Eigen::Matrix<double, -1, -1, 0, -1, -1>, Eigen::Product<Eigen::Inverse<Eigen::Product<Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, Eigen::Matrix<double, -1, -1, 0, -1, -1>, 0> >, Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, 0>, Eigen::internal::assign_op<double, double> >(Eigen::Matrix<double, -1, -1, 0, -1, -1>&, Eigen::Product<Eigen::Inverse<Eigen::Product<Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, Eigen::Matrix<double, -1, -1, 0, -1, -1>, 0> >, Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, 0> const&, Eigen::internal::assign_op<double, double> const&, Eigen::internal::enable_if<evaluator_assume_aliasing<Eigen::Product<Eigen::Inverse<Eigen::Product<Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, Eigen::Matrix<double, -1, -1, 0, -1, -1>, 0> >, Eigen::Transpose<Eigen::Matrix<double, -1, -1, 0, -1, -1> >, 0> >::value, void*>::type)@plt>
MultiSteersOdometer::CalOdoCoef():
  14cd03:	48 8d bc 24 f8 00 00 	lea    0xf8(%rsp),%rdi
  14cd0a:	00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:96
  14cd0b:	be 18 00 00 00       	mov    $0x18,%esi
  14cd10:	e8 bb 77 f3 ff       	call   844d0 <std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::basic_stringstream(std::_Ios_Openmode)@plt>
  14cd15:	48 8d bc 24 08 01 00 	lea    0x108(%rsp),%rdi
  14cd1c:	00 
std::basic_ostream<char, std::char_traits<char> >& std::operator<< <std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ostream:561
  14cd1d:	48 8d 35 31 35 05 00 	lea    0x53531(%rip),%rsi        # 1a0255 <typeinfo name for rbk::Logger::Thread::move2thread<DualDiffOdometer::CaldPose()::$_4>(DualDiffOdometer::CaldPose()::$_4&&)::{lambda()#1}+0x6d5>
  14cd24:	ba 2d 00 00 00       	mov    $0x2d,%edx
  14cd29:	e8 92 94 f3 ff       	call   861c0 <std::basic_ostream<char, std::char_traits<char> >& std::__ostream_insert<char, std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*, long)@plt>
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::str() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:779
  14cd2e:	48 8d b4 24 10 01 00 	lea    0x110(%rsp),%rsi
  14cd35:	00 
  14cd36:	48 8d bc 24 c8 00 00 	lea    0xc8(%rsp),%rdi
  14cd3d:	00 
  14cd3e:	e8 bd 75 f3 ff       	call   84300 <std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::str() const@plt>
MultiSteersOdometer::CalOdoCoef():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:96
  14cd43:	e8 98 71 f3 ff       	call   83ee0 <rbk::Logger::thread()@plt>
  14cd48:	49 89 c7             	mov    %rax,%r15
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:182
  14cd4b:	4c 8d ac 24 80 00 00 	lea    0x80(%rsp),%r13
  14cd52:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14cd53:	4c 89 6c 24 70       	mov    %r13,0x70(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14cd58:	4c 8b b4 24 c8 00 00 	mov    0xc8(%rsp),%r14
  14cd5f:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14cd60:	48 8b 9c 24 d0 00 00 	mov    0xd0(%rsp),%rbx
  14cd67:	00 
bool __gnu_cxx::__is_null_pointer<char>(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/type_traits.h:153
  14cd68:	4d 85 f6             	test   %r14,%r14
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:211
  14cd6b:	75 09                	jne    14cd76 <MultiSteersOdometer::CalOdoCoef()+0x386>
  14cd6d:	48 85 db             	test   %rbx,%rbx
  14cd70:	0f 85 08 06 00 00    	jne    14d37e <MultiSteersOdometer::CalOdoCoef()+0x98e>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:215
  14cd76:	48 89 5c 24 10       	mov    %rbx,0x10(%rsp)
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:217
  14cd7b:	48 83 fb 0f          	cmp    $0xf,%rbx
  14cd7f:	76 35                	jbe    14cdb6 <MultiSteersOdometer::CalOdoCoef()+0x3c6>
MultiSteersOdometer::CalOdoCoef():
  14cd81:	48 8d 7c 24 70       	lea    0x70(%rsp),%rdi
  14cd86:	48 8d 74 24 10       	lea    0x10(%rsp),%rsi
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:219
  14cd8b:	31 d2                	xor    %edx,%edx
  14cd8d:	e8 9e 83 f3 ff       	call   85130 <std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_create(unsigned long&, unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14cd92:	48 89 44 24 70       	mov    %rax,0x70(%rsp)
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:220
  14cd97:	48 8b 4c 24 10       	mov    0x10(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14cd9c:	48 89 8c 24 80 00 00 	mov    %rcx,0x80(%rsp)
  14cda3:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  14cda4:	48 85 db             	test   %rbx,%rbx
  14cda7:	74 25                	je     14cdce <MultiSteersOdometer::CalOdoCoef()+0x3de>
  14cda9:	48 83 fb 01          	cmp    $0x1,%rbx
  14cdad:	75 11                	jne    14cdc0 <MultiSteersOdometer::CalOdoCoef()+0x3d0>
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14cdaf:	41 8a 0e             	mov    (%r14),%cl
  14cdb2:	88 08                	mov    %cl,(%rax)
  14cdb4:	eb 18                	jmp    14cdce <MultiSteersOdometer::CalOdoCoef()+0x3de>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14cdb6:	4c 89 e8             	mov    %r13,%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_S_copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:337
  14cdb9:	48 85 db             	test   %rbx,%rbx
  14cdbc:	75 eb                	jne    14cda9 <MultiSteersOdometer::CalOdoCoef()+0x3b9>
  14cdbe:	eb 0e                	jmp    14cdce <MultiSteersOdometer::CalOdoCoef()+0x3de>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14cdc0:	48 89 c7             	mov    %rax,%rdi
  14cdc3:	4c 89 f6             	mov    %r14,%rsi
  14cdc6:	48 89 da             	mov    %rbx,%rdx
  14cdc9:	e8 a2 66 f3 ff       	call   83470 <memcpy@plt>
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:232
  14cdce:	48 8b 44 24 10       	mov    0x10(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14cdd3:	48 89 44 24 78       	mov    %rax,0x78(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14cdd8:	48 8b 4c 24 70       	mov    0x70(%rsp),%rcx
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14cddd:	c6 04 01 00          	movb   $0x0,(%rcx,%rax,1)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:182
  14cde1:	4c 8d 74 24 20       	lea    0x20(%rsp),%r14
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14cde6:	4c 89 74 24 10       	mov    %r14,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14cdeb:	48 8b 5c 24 70       	mov    0x70(%rsp),%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14cdf0:	4c 39 eb             	cmp    %r13,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:534
  14cdf3:	74 14                	je     14ce09 <MultiSteersOdometer::CalOdoCoef()+0x419>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14cdf5:	48 89 5c 24 10       	mov    %rbx,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:542
  14cdfa:	48 8b 84 24 80 00 00 	mov    0x80(%rsp),%rax
  14ce01:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14ce02:	48 89 44 24 20       	mov    %rax,0x20(%rsp)
  14ce07:	eb 0e                	jmp    14ce17 <MultiSteersOdometer::CalOdoCoef()+0x427>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14ce09:	66 41 0f 10 45 00    	movupd 0x0(%r13),%xmm0
  14ce0f:	66 41 0f 11 06       	movupd %xmm0,(%r14)
  14ce14:	4c 89 f3             	mov    %r14,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14ce17:	4c 8b 64 24 78       	mov    0x78(%rsp),%r12
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14ce1c:	4c 89 64 24 18       	mov    %r12,0x18(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14ce21:	4c 89 6c 24 70       	mov    %r13,0x70(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14ce26:	48 c7 44 24 78 00 00 	movq   $0x0,0x78(%rsp)
  14ce2d:	00 00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14ce2f:	c6 84 24 80 00 00 00 	movb   $0x0,0x80(%rsp)
  14ce36:	00 
std::_Function_base::_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:271
  14ce37:	48 c7 44 24 60 00 00 	movq   $0x0,0x60(%rsp)
  14ce3e:	00 00 
std::_Function_base::_Base_manager<std::_Bind<MultiSteersOdometer::CalOdoCoef()::$_1 ()> >::_M_init_functor(std::_Any_data&, std::_Bind<MultiSteersOdometer::CalOdoCoef()::$_1 ()>&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14ce40:	bf 28 00 00 00       	mov    $0x28,%edi
  14ce45:	e8 76 68 f3 ff       	call   836c0 <operator new(unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:182
  14ce4a:	48 89 c1             	mov    %rax,%rcx
  14ce4d:	48 83 c1 10          	add    $0x10,%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14ce51:	48 89 08             	mov    %rcx,(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14ce54:	4c 39 f3             	cmp    %r14,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:534
  14ce57:	74 0e                	je     14ce67 <MultiSteersOdometer::CalOdoCoef()+0x477>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14ce59:	48 89 18             	mov    %rbx,(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:542
  14ce5c:	48 8b 4c 24 20       	mov    0x20(%rsp),%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14ce61:	48 89 48 10          	mov    %rcx,0x10(%rax)
  14ce65:	eb 09                	jmp    14ce70 <MultiSteersOdometer::CalOdoCoef()+0x480>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14ce67:	66 41 0f 10 06       	movupd (%r14),%xmm0
  14ce6c:	66 0f 11 01          	movupd %xmm0,(%rcx)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14ce70:	4c 89 74 24 10       	mov    %r14,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14ce75:	48 c7 44 24 18 00 00 	movq   $0x0,0x18(%rsp)
  14ce7c:	00 00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14ce7e:	c6 44 24 20 00       	movb   $0x0,0x20(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14ce83:	4c 89 60 08          	mov    %r12,0x8(%rax)
std::_Function_base::_Base_manager<std::_Bind<MultiSteersOdometer::CalOdoCoef()::$_1 ()> >::_M_init_functor(std::_Any_data&, std::_Bind<MultiSteersOdometer::CalOdoCoef()::$_1 ()>&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14ce87:	48 89 44 24 50       	mov    %rax,0x50(%rsp)
std::function<void ()>::function<std::_Bind<MultiSteersOdometer::CalOdoCoef()::$_1 ()>, void, void>(std::_Bind<MultiSteersOdometer::CalOdoCoef()::$_1 ()>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:694
  14ce8c:	48 8d 05 4d 34 00 00 	lea    0x344d(%rip),%rax        # 1502e0 <std::_Function_handler<void (), std::_Bind<MultiSteersOdometer::CalOdoCoef()::$_1 ()> >::_M_invoke(std::_Any_data const&)>
  14ce93:	48 89 44 24 68       	mov    %rax,0x68(%rsp)
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:695
  14ce98:	48 8d 05 21 36 00 00 	lea    0x3621(%rip),%rax        # 1504c0 <std::_Function_base::_Base_manager<std::_Bind<MultiSteersOdometer::CalOdoCoef()::$_1 ()> >::_M_manager(std::_Any_data&, std::_Any_data const&, std::_Manager_operation)>
  14ce9f:	48 89 44 24 60       	mov    %rax,0x60(%rsp)
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1294
  14cea4:	48 c7 44 24 40 00 00 	movq   $0x0,0x40(%rsp)
  14ceab:	00 00 
  14cead:	48 8d 7c 24 48       	lea    0x48(%rsp),%rdi
MultiSteersOdometer::CalOdoCoef():
  14ceb2:	48 8d 94 24 90 00 00 	lea    0x90(%rsp),%rdx
  14ceb9:	00 
  14ceba:	48 8d 4c 24 50       	lea    0x50(%rsp),%rcx
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1294
  14cebf:	31 f6                	xor    %esi,%esi
  14cec1:	e8 7a 9c f3 ff       	call   86b40 <std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count<std::packaged_task<void ()>, std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::packaged_task<void ()>*, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&)@plt>
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_get_deleter(std::type_info const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:727
  14cec6:	48 8b 7c 24 48       	mov    0x48(%rsp),%rdi
  14cecb:	48 85 ff             	test   %rdi,%rdi
  14cece:	74 17                	je     14cee7 <MultiSteersOdometer::CalOdoCoef()+0x4f7>
  14ced0:	48 8b 07             	mov    (%rdi),%rax
  14ced3:	48 8b 35 76 a9 2b 00 	mov    0x2ba976(%rip),%rsi        # 407850 <typeinfo for std::_Sp_make_shared_tag@@Base+0x6d08>
  14ceda:	ff 50 20             	call   *0x20(%rax)
  14cedd:	48 89 c3             	mov    %rax,%rbx
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:688
  14cee0:	4c 8b 64 24 48       	mov    0x48(%rsp),%r12
  14cee5:	eb 05                	jmp    14ceec <MultiSteersOdometer::CalOdoCoef()+0x4fc>
MultiSteersOdometer::CalOdoCoef():
  14cee7:	45 31 e4             	xor    %r12d,%r12d
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_get_deleter(std::type_info const&) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:727
  14ceea:	31 db                	xor    %ebx,%ebx
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr<std::allocator<std::packaged_task<void ()> >, std::function<void ()>&>(std::_Sp_make_shared_tag, std::allocator<std::packaged_task<void ()> > const&, std::function<void ()>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1300
  14ceec:	48 89 5c 24 40       	mov    %rbx,0x40(%rsp)
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:690
  14cef1:	4d 85 e4             	test   %r12,%r12
  14cef4:	74 19                	je     14cf0f <MultiSteersOdometer::CalOdoCoef()+0x51f>
__gnu_cxx::__atomic_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:95
  14cef6:	48 83 3d aa ab 2b 00 	cmpq   $0x0,0x2babaa(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14cefd:	00 
  14cefe:	74 09                	je     14cf09 <MultiSteersOdometer::CalOdoCoef()+0x519>
__gnu_cxx::__atomic_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:53
  14cf00:	f0 41 83 44 24 08 01 	lock addl $0x1,0x8(%r12)
  14cf07:	eb 06                	jmp    14cf0f <MultiSteersOdometer::CalOdoCoef()+0x51f>
__gnu_cxx::__atomic_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:74
  14cf09:	41 83 44 24 08 01    	addl   $0x1,0x8(%r12)
std::_Function_base::_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:271
  14cf0f:	48 c7 84 24 a0 00 00 	movq   $0x0,0xa0(%rsp)
  14cf16:	00 00 00 00 00 
std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalOdoCoef()::$_1>(MultiSteersOdometer::CalOdoCoef()::$_1&&)::{lambda()#1}>::_M_init_functor(std::_Any_data&, rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalOdoCoef()::$_1>(MultiSteersOdometer::CalOdoCoef()::$_1&&)::{lambda()#1}&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14cf1b:	bf 10 00 00 00       	mov    $0x10,%edi
  14cf20:	e8 9b 67 f3 ff       	call   836c0 <operator new(unsigned long)@plt>
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::__shared_ptr(std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1131
  14cf25:	48 89 18             	mov    %rbx,(%rax)
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::_M_swap(std::__shared_count<(__gnu_cxx::_Lock_policy)2>&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:714
  14cf28:	4c 89 60 08          	mov    %r12,0x8(%rax)
std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalOdoCoef()::$_1>(MultiSteersOdometer::CalOdoCoef()::$_1&&)::{lambda()#1}>::_M_init_functor(std::_Any_data&, rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalOdoCoef()::$_1>(MultiSteersOdometer::CalOdoCoef()::$_1&&)::{lambda()#1}&&, std::integral_constant<bool, false>):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:268
  14cf2c:	48 89 84 24 90 00 00 	mov    %rax,0x90(%rsp)
  14cf33:	00 
std::function<void ()>::function<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalOdoCoef()::$_1>(MultiSteersOdometer::CalOdoCoef()::$_1&&)::{lambda()#1}, void, void>(rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalOdoCoef()::$_1>(MultiSteersOdometer::CalOdoCoef()::$_1&&)::{lambda()#1}):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:694
  14cf34:	48 8d 05 b5 36 00 00 	lea    0x36b5(%rip),%rax        # 1505f0 <std::_Function_handler<void (), rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalOdoCoef()::$_1>(MultiSteersOdometer::CalOdoCoef()::$_1&&)::{lambda()#1}>::_M_invoke(std::_Any_data const&)>
  14cf3b:	48 89 84 24 a8 00 00 	mov    %rax,0xa8(%rsp)
  14cf42:	00 
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:695
  14cf43:	48 8d 05 d6 36 00 00 	lea    0x36d6(%rip),%rax        # 150620 <std::_Function_base::_Base_manager<rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalOdoCoef()::$_1>(MultiSteersOdometer::CalOdoCoef()::$_1&&)::{lambda()#1}>::_M_manager(std::_Any_data&, std::_Any_data const&, std::_Manager_operation)>
  14cf4a:	48 89 84 24 a0 00 00 	mov    %rax,0xa0(%rsp)
  14cf51:	00 
std::future<decltype ({parm#1}({parm#2}...))> rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalOdoCoef()::$_1>(MultiSteersOdometer::CalOdoCoef()::$_1&&):
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:204
  14cf52:	49 8d 7f 08          	lea    0x8(%r15),%rdi
  14cf56:	48 8d b4 24 90 00 00 	lea    0x90(%rsp),%rsi
  14cf5d:	00 
  14cf5e:	e8 4d 6e f3 ff       	call   83db0 <rbk::Logger::Thread::SafeQueue<std::function<void ()> >::push_back(std::function<void ()>&)@plt>
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:206
  14cf63:	49 81 c7 c0 01 00 00 	add    $0x1c0,%r15
  14cf6a:	4c 89 ff             	mov    %r15,%rdi
  14cf6d:	e8 3e 7d f3 ff       	call   84cb0 <std::condition_variable::notify_one()@plt>
std::__shared_ptr<std::packaged_task<void ()>, (__gnu_cxx::_Lock_policy)2>::get() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:1258
  14cf72:	48 8b 74 24 40       	mov    0x40(%rsp),%rsi
  14cf77:	48 8d bc 24 e8 00 00 	lea    0xe8(%rsp),%rdi
  14cf7e:	00 
std::future<decltype ({parm#1}({parm#2}...))> rbk::Logger::Thread::move2thread<MultiSteersOdometer::CalOdoCoef()::$_1>(MultiSteersOdometer::CalOdoCoef()::$_1&&):
/root/workspace/3.4.5.20/src/robokit/utils/logger/logger.h:207
  14cf7f:	e8 cc 8f f3 ff       	call   85f50 <std::packaged_task<void ()>::get_future()@plt>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14cf84:	48 8b 84 24 a0 00 00 	mov    0xa0(%rsp),%rax
  14cf8b:	00 
  14cf8c:	48 85 c0             	test   %rax,%rax
  14cf8f:	4c 8b 7c 24 08       	mov    0x8(%rsp),%r15
  14cf94:	74 12                	je     14cfa8 <MultiSteersOdometer::CalOdoCoef()+0x5b8>
MultiSteersOdometer::CalOdoCoef():
  14cf96:	48 8d bc 24 90 00 00 	lea    0x90(%rsp),%rdi
  14cf9d:	00 
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14cf9e:	ba 03 00 00 00       	mov    $0x3,%edx
  14cfa3:	48 89 fe             	mov    %rdi,%rsi
  14cfa6:	ff d0                	call   *%rax
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14cfa8:	48 8b 5c 24 48       	mov    0x48(%rsp),%rbx
  14cfad:	48 85 db             	test   %rbx,%rbx
  14cfb0:	74 64                	je     14d016 <MultiSteersOdometer::CalOdoCoef()+0x626>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14cfb2:	48 83 3d ee aa 2b 00 	cmpq   $0x0,0x2baaee(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14cfb9:	00 
  14cfba:	74 11                	je     14cfcd <MultiSteersOdometer::CalOdoCoef()+0x5dd>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14cfbc:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14cfc1:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14cfc6:	83 f8 01             	cmp    $0x1,%eax
  14cfc9:	74 10                	je     14cfdb <MultiSteersOdometer::CalOdoCoef()+0x5eb>
  14cfcb:	eb 49                	jmp    14d016 <MultiSteersOdometer::CalOdoCoef()+0x626>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14cfcd:	8b 43 08             	mov    0x8(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14cfd0:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14cfd3:	89 4b 08             	mov    %ecx,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14cfd6:	83 f8 01             	cmp    $0x1,%eax
  14cfd9:	75 3b                	jne    14d016 <MultiSteersOdometer::CalOdoCoef()+0x626>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14cfdb:	48 8b 03             	mov    (%rbx),%rax
  14cfde:	48 89 df             	mov    %rbx,%rdi
  14cfe1:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14cfe4:	48 83 3d bc aa 2b 00 	cmpq   $0x0,0x2baabc(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14cfeb:	00 
  14cfec:	74 11                	je     14cfff <MultiSteersOdometer::CalOdoCoef()+0x60f>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14cfee:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14cff3:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14cff8:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14cffb:	74 10                	je     14d00d <MultiSteersOdometer::CalOdoCoef()+0x61d>
  14cffd:	eb 17                	jmp    14d016 <MultiSteersOdometer::CalOdoCoef()+0x626>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14cfff:	8b 43 0c             	mov    0xc(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14d002:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14d005:	89 4b 0c             	mov    %ecx,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14d008:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14d00b:	75 09                	jne    14d016 <MultiSteersOdometer::CalOdoCoef()+0x626>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14d00d:	48 8b 03             	mov    (%rbx),%rax
  14d010:	48 89 df             	mov    %rbx,%rdi
  14d013:	ff 50 18             	call   *0x18(%rax)
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14d016:	48 8b 44 24 60       	mov    0x60(%rsp),%rax
  14d01b:	48 85 c0             	test   %rax,%rax
  14d01e:	74 0f                	je     14d02f <MultiSteersOdometer::CalOdoCoef()+0x63f>
MultiSteersOdometer::CalOdoCoef():
  14d020:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14d025:	ba 03 00 00 00       	mov    $0x3,%edx
  14d02a:	48 89 fe             	mov    %rdi,%rsi
  14d02d:	ff d0                	call   *%rax
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14d02f:	48 8b 9c 24 f0 00 00 	mov    0xf0(%rsp),%rbx
  14d036:	00 
  14d037:	48 85 db             	test   %rbx,%rbx
  14d03a:	74 64                	je     14d0a0 <MultiSteersOdometer::CalOdoCoef()+0x6b0>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14d03c:	48 83 3d 64 aa 2b 00 	cmpq   $0x0,0x2baa64(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14d043:	00 
  14d044:	74 11                	je     14d057 <MultiSteersOdometer::CalOdoCoef()+0x667>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14d046:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14d04b:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14d050:	83 f8 01             	cmp    $0x1,%eax
  14d053:	74 10                	je     14d065 <MultiSteersOdometer::CalOdoCoef()+0x675>
  14d055:	eb 49                	jmp    14d0a0 <MultiSteersOdometer::CalOdoCoef()+0x6b0>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14d057:	8b 43 08             	mov    0x8(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14d05a:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14d05d:	89 4b 08             	mov    %ecx,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14d060:	83 f8 01             	cmp    $0x1,%eax
  14d063:	75 3b                	jne    14d0a0 <MultiSteersOdometer::CalOdoCoef()+0x6b0>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14d065:	48 8b 03             	mov    (%rbx),%rax
  14d068:	48 89 df             	mov    %rbx,%rdi
  14d06b:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14d06e:	48 83 3d 32 aa 2b 00 	cmpq   $0x0,0x2baa32(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14d075:	00 
  14d076:	74 11                	je     14d089 <MultiSteersOdometer::CalOdoCoef()+0x699>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14d078:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14d07d:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14d082:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14d085:	74 10                	je     14d097 <MultiSteersOdometer::CalOdoCoef()+0x6a7>
  14d087:	eb 17                	jmp    14d0a0 <MultiSteersOdometer::CalOdoCoef()+0x6b0>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14d089:	8b 43 0c             	mov    0xc(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14d08c:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14d08f:	89 4b 0c             	mov    %ecx,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14d092:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14d095:	75 09                	jne    14d0a0 <MultiSteersOdometer::CalOdoCoef()+0x6b0>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14d097:	48 8b 03             	mov    (%rbx),%rax
  14d09a:	48 89 df             	mov    %rbx,%rdi
  14d09d:	ff 50 18             	call   *0x18(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d0a0:	48 8b 7c 24 70       	mov    0x70(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d0a5:	4c 39 ef             	cmp    %r13,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d0a8:	74 05                	je     14d0af <MultiSteersOdometer::CalOdoCoef()+0x6bf>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d0aa:	e8 81 79 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d0af:	48 8b bc 24 c8 00 00 	mov    0xc8(%rsp),%rdi
  14d0b6:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14d0b7:	48 8d 84 24 d8 00 00 	lea    0xd8(%rsp),%rax
  14d0be:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d0bf:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d0c2:	74 05                	je     14d0c9 <MultiSteersOdometer::CalOdoCoef()+0x6d9>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d0c4:	e8 67 79 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::~basic_stringstream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:731
  14d0c9:	48 8b 1d 98 a9 2b 00 	mov    0x2ba998(%rip),%rbx        # 407a68 <VTT for std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  14d0d0:	48 8b 03             	mov    (%rbx),%rax
  14d0d3:	48 89 84 24 f8 00 00 	mov    %rax,0xf8(%rsp)
  14d0da:	00 
  14d0db:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  14d0df:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14d0e3:	48 89 8c 04 f8 00 00 	mov    %rcx,0xf8(%rsp,%rax,1)
  14d0ea:	00 
  14d0eb:	48 8b 43 48          	mov    0x48(%rbx),%rax
  14d0ef:	48 89 84 24 08 01 00 	mov    %rax,0x108(%rsp)
  14d0f6:	00 
std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::~basic_stringbuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/sstream.tcc:291
  14d0f7:	48 8b 05 6a 9d 2b 00 	mov    0x2b9d6a(%rip),%rax        # 406e68 <vtable for std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  14d0fe:	48 83 c0 10          	add    $0x10,%rax
  14d102:	48 89 84 24 10 01 00 	mov    %rax,0x110(%rsp)
  14d109:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d10a:	48 8b bc 24 58 01 00 	mov    0x158(%rsp),%rdi
  14d111:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14d112:	48 8d 84 24 68 01 00 	lea    0x168(%rsp),%rax
  14d119:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d11a:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d11d:	74 05                	je     14d124 <MultiSteersOdometer::CalOdoCoef()+0x734>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d11f:	e8 0c 79 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::basic_streambuf<char, std::char_traits<char> >::~basic_streambuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/streambuf:198
  14d124:	48 8b 05 ed a7 2b 00 	mov    0x2ba7ed(%rip),%rax        # 407918 <vtable for std::basic_streambuf<char, std::char_traits<char> >@GLIBCXX_3.4>
  14d12b:	48 83 c0 10          	add    $0x10,%rax
  14d12f:	48 89 84 24 10 01 00 	mov    %rax,0x110(%rsp)
  14d136:	00 
  14d137:	48 8d bc 24 48 01 00 	lea    0x148(%rsp),%rdi
  14d13e:	00 
  14d13f:	e8 ec 90 f3 ff       	call   86230 <std::locale::~locale()@plt>
std::basic_istream<char, std::char_traits<char> >::~basic_istream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/istream:104
  14d144:	48 8b 43 10          	mov    0x10(%rbx),%rax
  14d148:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  14d14c:	48 89 84 24 f8 00 00 	mov    %rax,0xf8(%rsp)
  14d153:	00 
  14d154:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14d158:	48 89 8c 04 f8 00 00 	mov    %rcx,0xf8(%rsp,%rax,1)
  14d15f:	00 
  14d160:	48 c7 84 24 00 01 00 	movq   $0x0,0x100(%rsp)
  14d167:	00 00 00 00 00 
std::basic_ios<char, std::char_traits<char> >::~basic_ios():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:282
  14d16c:	48 8d bc 24 78 01 00 	lea    0x178(%rsp),%rdi
  14d173:	00 
  14d174:	e8 a7 81 f3 ff       	call   85320 <std::ios_base::~ios_base()@plt>
MultiSteersOdometer::CalOdoCoef():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:98
  14d179:	41 80 7f 0c 00       	cmpb   $0x0,0xc(%r15)
  14d17e:	0f 84 d8 01 00 00    	je     14d35c <MultiSteersOdometer::CalOdoCoef()+0x96c>
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:99
  14d184:	e8 07 8d f3 ff       	call   85e90 <rbk::utils::filesystem::FileSystem::instance()@plt>
  14d189:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:100
  14d18e:	48 89 c6             	mov    %rax,%rsi
  14d191:	e8 7a 9b f3 ff       	call   86d10 <rbk::utils::filesystem::FileSystem::rbkUserDataDir[abi:cxx11]() const@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_check_length(unsigned long, unsigned long, char const*) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:311
  14d196:	48 b8 ff ff ff ff ff 	movabs $0x7fffffffffffffff,%rax
  14d19d:	ff ff 7f 
  14d1a0:	48 2b 44 24 58       	sub    0x58(%rsp),%rax
  14d1a5:	48 83 f8 2c          	cmp    $0x2c,%rax
  14d1a9:	0f 86 db 01 00 00    	jbe    14d38a <MultiSteersOdometer::CalOdoCoef()+0x99a>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::append(char const*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:1258
  14d1af:	48 8d 35 f0 18 05 00 	lea    0x518f0(%rip),%rsi        # 19eaa6 <typeinfo name for rbk::Logger::Thread::move2thread<AckermanOdometer::CaldPose()::$_2>(AckermanOdometer::CaldPose()::$_2&&)::{lambda()#1}+0x146>
MultiSteersOdometer::CalOdoCoef():
  14d1b6:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::append(char const*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:1258
  14d1bb:	ba 2d 00 00 00       	mov    $0x2d,%edx
  14d1c0:	e8 db 82 f3 ff       	call   854a0 <std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_append(char const*, unsigned long)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_Alloc_hider::_Alloc_hider(char*, std::allocator<char>&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:149
  14d1c5:	4c 89 74 24 10       	mov    %r14,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d1ca:	48 8b 10             	mov    (%rax),%rdx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14d1cd:	48 89 c1             	mov    %rax,%rcx
  14d1d0:	48 83 c1 10          	add    $0x10,%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d1d4:	48 39 ca             	cmp    %rcx,%rdx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:534
  14d1d7:	74 10                	je     14d1e9 <MultiSteersOdometer::CalOdoCoef()+0x7f9>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14d1d9:	48 89 54 24 10       	mov    %rdx,0x10(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:542
  14d1de:	48 8b 50 10          	mov    0x10(%rax),%rdx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_capacity(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:200
  14d1e2:	48 89 54 24 20       	mov    %rdx,0x20(%rsp)
  14d1e7:	eb 09                	jmp    14d1f2 <MultiSteersOdometer::CalOdoCoef()+0x802>
std::char_traits<char>::copy(char*, char const*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:350
  14d1e9:	66 0f 10 02          	movupd (%rdx),%xmm0
  14d1ed:	66 41 0f 11 06       	movupd %xmm0,(%r14)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::length() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:927
  14d1f2:	48 8b 50 08          	mov    0x8(%rax),%rdx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14d1f6:	48 89 54 24 18       	mov    %rdx,0x18(%rsp)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data(char*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:168
  14d1fb:	48 89 08             	mov    %rcx,(%rax)
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_length(unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:172
  14d1fe:	48 c7 40 08 00 00 00 	movq   $0x0,0x8(%rax)
  14d205:	00 
std::char_traits<char>::assign(char&, char const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/char_traits.h:285
  14d206:	c6 40 10 00          	movb   $0x0,0x10(%rax)
  14d20a:	48 8d bc 24 f8 00 00 	lea    0xf8(%rsp),%rdi
  14d211:	00 
  14d212:	48 8d 74 24 10       	lea    0x10(%rsp),%rsi
MultiSteersOdometer::CalOdoCoef():
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:99
  14d217:	ba 30 00 00 00       	mov    $0x30,%edx
  14d21c:	e8 6f 64 f3 ff       	call   83690 <std::basic_ofstream<char, std::char_traits<char> >::basic_ofstream(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&, std::_Ios_Openmode)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d221:	48 8b 7c 24 10       	mov    0x10(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d226:	4c 39 f7             	cmp    %r14,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d229:	74 05                	je     14d230 <MultiSteersOdometer::CalOdoCoef()+0x840>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d22b:	e8 00 78 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d230:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14d235:	48 8d 44 24 60       	lea    0x60(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d23a:	48 39 c7             	cmp    %rax,%rdi
  14d23d:	4c 8b 74 24 38       	mov    0x38(%rsp),%r14
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d242:	74 05                	je     14d249 <MultiSteersOdometer::CalOdoCoef()+0x859>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d244:	e8 e7 77 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::basic_ostream<char, std::char_traits<char> >& std::operator<< <std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ostream:561
  14d249:	48 8d 35 84 18 05 00 	lea    0x51884(%rip),%rsi        # 19ead4 <typeinfo name for rbk::Logger::Thread::move2thread<AckermanOdometer::CaldPose()::$_2>(AckermanOdometer::CaldPose()::$_2&&)::{lambda()#1}+0x174>
MultiSteersOdometer::CalOdoCoef():
  14d250:	48 8d bc 24 f8 00 00 	lea    0xf8(%rsp),%rdi
  14d257:	00 
std::basic_ostream<char, std::char_traits<char> >& std::operator<< <std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ostream:561
  14d258:	ba 02 00 00 00       	mov    $0x2,%edx
  14d25d:	e8 5e 8f f3 ff       	call   861c0 <std::basic_ostream<char, std::char_traits<char> >& std::__ostream_insert<char, std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*, long)@plt>
std::basic_ostream<char, std::char_traits<char> >& std::endl<char, std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ostream:591
  14d262:	48 8b 84 24 f8 00 00 	mov    0xf8(%rsp),%rax
  14d269:	00 
  14d26a:	48 8b 40 e8          	mov    -0x18(%rax),%rax
std::basic_ios<char, std::char_traits<char> >::widen(char) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:450
  14d26e:	48 8b 9c 04 e8 01 00 	mov    0x1e8(%rsp,%rax,1),%rbx
  14d275:	00 
std::ctype<char> const& std::__check_facet<std::ctype<char> >(std::ctype<char> const*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:49
  14d276:	48 85 db             	test   %rbx,%rbx
  14d279:	0f 84 17 01 00 00    	je     14d396 <MultiSteersOdometer::CalOdoCoef()+0x9a6>
std::ctype<char>::widen(char) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/locale_facets.h:874
  14d27f:	80 7b 38 00          	cmpb   $0x0,0x38(%rbx)
  14d283:	74 05                	je     14d28a <MultiSteersOdometer::CalOdoCoef()+0x89a>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/locale_facets.h:875
  14d285:	8a 43 43             	mov    0x43(%rbx),%al
  14d288:	eb 16                	jmp    14d2a0 <MultiSteersOdometer::CalOdoCoef()+0x8b0>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/locale_facets.h:876
  14d28a:	48 89 df             	mov    %rbx,%rdi
  14d28d:	e8 0e 74 f3 ff       	call   846a0 <std::ctype<char>::_M_widen_init() const@plt>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/locale_facets.h:877
  14d292:	48 8b 03             	mov    (%rbx),%rax
  14d295:	be 0a 00 00 00       	mov    $0xa,%esi
  14d29a:	48 89 df             	mov    %rbx,%rdi
  14d29d:	ff 50 30             	call   *0x30(%rax)
std::basic_ostream<char, std::char_traits<char> >& std::endl<char, std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ostream:591
  14d2a0:	0f be f0             	movsbl %al,%esi
  14d2a3:	48 8d bc 24 f8 00 00 	lea    0xf8(%rsp),%rdi
  14d2aa:	00 
  14d2ab:	e8 90 77 f3 ff       	call   84a40 <std::ostream::put(char)@plt>
std::basic_ostream<char, std::char_traits<char> >& std::flush<char, std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ostream:613
  14d2b0:	48 89 c7             	mov    %rax,%rdi
  14d2b3:	e8 88 74 f3 ff       	call   84740 <std::ostream::flush()@plt>
MultiSteersOdometer::CalOdoCoef():
  14d2b8:	48 8d bc 24 f8 00 00 	lea    0xf8(%rsp),%rdi
  14d2bf:	00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:102
  14d2c0:	4c 89 f6             	mov    %r14,%rsi
  14d2c3:	e8 b8 89 f3 ff       	call   85c80 <std::ostream& Eigen::operator<< <Eigen::Matrix<double, -1, -1, 0, -1, -1> >(std::ostream&, Eigen::DenseBase<Eigen::Matrix<double, -1, -1, 0, -1, -1> > const&)@plt>
  14d2c8:	49 89 c6             	mov    %rax,%r14
std::basic_ostream<char, std::char_traits<char> >& std::endl<char, std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ostream:591
  14d2cb:	49 8b 06             	mov    (%r14),%rax
  14d2ce:	48 8b 40 e8          	mov    -0x18(%rax),%rax
std::basic_ios<char, std::char_traits<char> >::widen(char) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:450
  14d2d2:	49 8b 9c 06 f0 00 00 	mov    0xf0(%r14,%rax,1),%rbx
  14d2d9:	00 
std::ctype<char> const& std::__check_facet<std::ctype<char> >(std::ctype<char> const*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:49
  14d2da:	48 85 db             	test   %rbx,%rbx
  14d2dd:	0f 84 b8 00 00 00    	je     14d39b <MultiSteersOdometer::CalOdoCoef()+0x9ab>
std::ctype<char>::widen(char) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/locale_facets.h:874
  14d2e3:	80 7b 38 00          	cmpb   $0x0,0x38(%rbx)
  14d2e7:	74 05                	je     14d2ee <MultiSteersOdometer::CalOdoCoef()+0x8fe>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/locale_facets.h:875
  14d2e9:	8a 43 43             	mov    0x43(%rbx),%al
  14d2ec:	eb 16                	jmp    14d304 <MultiSteersOdometer::CalOdoCoef()+0x914>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/locale_facets.h:876
  14d2ee:	48 89 df             	mov    %rbx,%rdi
  14d2f1:	e8 aa 73 f3 ff       	call   846a0 <std::ctype<char>::_M_widen_init() const@plt>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/locale_facets.h:877
  14d2f6:	48 8b 03             	mov    (%rbx),%rax
  14d2f9:	be 0a 00 00 00       	mov    $0xa,%esi
  14d2fe:	48 89 df             	mov    %rbx,%rdi
  14d301:	ff 50 30             	call   *0x30(%rax)
std::basic_ostream<char, std::char_traits<char> >& std::endl<char, std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ostream:591
  14d304:	0f be f0             	movsbl %al,%esi
  14d307:	4c 89 f7             	mov    %r14,%rdi
  14d30a:	e8 31 77 f3 ff       	call   84a40 <std::ostream::put(char)@plt>
std::basic_ostream<char, std::char_traits<char> >& std::flush<char, std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ostream:613
  14d30f:	48 89 c7             	mov    %rax,%rdi
  14d312:	e8 29 74 f3 ff       	call   84740 <std::ostream::flush()@plt>
std::basic_ofstream<char, std::char_traits<char> >::close():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/fstream:841
  14d317:	48 8d bc 24 00 01 00 	lea    0x100(%rsp),%rdi
  14d31e:	00 
  14d31f:	e8 ac 65 f3 ff       	call   838d0 <std::basic_filebuf<char, std::char_traits<char> >::close()@plt>
  14d324:	48 85 c0             	test   %rax,%rax
  14d327:	75 26                	jne    14d34f <MultiSteersOdometer::CalOdoCoef()+0x95f>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/fstream:842
  14d329:	48 8b 84 24 f8 00 00 	mov    0xf8(%rsp),%rax
  14d330:	00 
  14d331:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14d335:	48 8d 3c 04          	lea    (%rsp,%rax,1),%rdi
  14d339:	48 81 c7 f8 00 00 00 	add    $0xf8,%rdi
std::basic_ios<char, std::char_traits<char> >::rdstate() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:138
  14d340:	8b b4 04 18 01 00 00 	mov    0x118(%rsp,%rax,1),%esi
std::operator|(std::_Ios_Iostate, std::_Ios_Iostate):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/ios_base.h:170
  14d347:	83 ce 04             	or     $0x4,%esi
std::basic_ios<char, std::char_traits<char> >::setstate(std::_Ios_Iostate):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:158
  14d34a:	e8 f1 95 f3 ff       	call   86940 <std::basic_ios<char, std::char_traits<char> >::clear(std::_Ios_Iostate)@plt>
MultiSteersOdometer::CalOdoCoef():
  14d34f:	48 8d bc 24 f8 00 00 	lea    0xf8(%rsp),%rdi
  14d356:	00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:104
  14d357:	e8 94 82 f3 ff       	call   855f0 <std::basic_ofstream<char, std::char_traits<char> >::~basic_ofstream()@plt>
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:106
  14d35c:	41 c6 47 0a 01       	movb   $0x1,0xa(%r15)
  14d361:	b0 01                	mov    $0x1,%al
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:107
  14d363:	48 8d 65 d8          	lea    -0x28(%rbp),%rsp
  14d367:	5b                   	pop    %rbx
  14d368:	41 5c                	pop    %r12
  14d36a:	41 5d                	pop    %r13
  14d36c:	41 5e                	pop    %r14
  14d36e:	41 5f                	pop    %r15
  14d370:	5d                   	pop    %rbp
  14d371:	c3                   	ret    
void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char*>(char*, char*, std::forward_iterator_tag):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.tcc:212
  14d372:	48 8d 3d 3c 07 04 00 	lea    0x4073c(%rip),%rdi        # 18dab5 <typeinfo name for rbk::Logger::Thread::move2thread<OdoCalculator::run()::$_32>(OdoCalculator::run()::$_32&&)::{lambda()#1}+0x1755>
  14d379:	e8 b2 5f f3 ff       	call   83330 <std::__throw_logic_error(char const*)@plt>
  14d37e:	48 8d 3d 30 07 04 00 	lea    0x40730(%rip),%rdi        # 18dab5 <typeinfo name for rbk::Logger::Thread::move2thread<OdoCalculator::run()::$_32>(OdoCalculator::run()::$_32&&)::{lambda()#1}+0x1755>
  14d385:	e8 a6 5f f3 ff       	call   83330 <std::__throw_logic_error(char const*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_check_length(unsigned long, unsigned long, char const*) const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:312
  14d38a:	48 8d 3d 0c 07 04 00 	lea    0x4070c(%rip),%rdi        # 18da9d <typeinfo name for rbk::Logger::Thread::move2thread<OdoCalculator::run()::$_32>(OdoCalculator::run()::$_32&&)::{lambda()#1}+0x173d>
  14d391:	e8 ca 79 f3 ff       	call   84d60 <std::__throw_length_error(char const*)@plt>
std::ctype<char> const& std::__check_facet<std::ctype<char> >(std::ctype<char> const*):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:50
  14d396:	e8 35 6c f3 ff       	call   83fd0 <std::__throw_bad_cast()@plt>
  14d39b:	e8 30 6c f3 ff       	call   83fd0 <std::__throw_bad_cast()@plt>
MultiSteersOdometer::CalOdoCoef():
  14d3a0:	e9 ef 00 00 00       	jmp    14d494 <MultiSteersOdometer::CalOdoCoef()+0xaa4>
  14d3a5:	49 89 c7             	mov    %rax,%r15
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d3a8:	48 8b 7c 24 10       	mov    0x10(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d3ad:	4c 39 f7             	cmp    %r14,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d3b0:	74 0a                	je     14d3bc <MultiSteersOdometer::CalOdoCoef()+0x9cc>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d3b2:	e8 79 76 f3 ff       	call   84a30 <operator delete(void*)@plt>
MultiSteersOdometer::CalOdoCoef():
  14d3b7:	eb 03                	jmp    14d3bc <MultiSteersOdometer::CalOdoCoef()+0x9cc>
  14d3b9:	49 89 c7             	mov    %rax,%r15
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d3bc:	48 8b 7c 24 50       	mov    0x50(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14d3c1:	48 8d 44 24 60       	lea    0x60(%rsp),%rax
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d3c6:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d3c9:	0f 84 a7 02 00 00    	je     14d676 <MultiSteersOdometer::CalOdoCoef()+0xc86>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d3cf:	e8 5c 76 f3 ff       	call   84a30 <operator delete(void*)@plt>
MultiSteersOdometer::CalOdoCoef():
  14d3d4:	4c 89 ff             	mov    %r15,%rdi
  14d3d7:	e8 a4 7b f3 ff       	call   84f80 <_Unwind_Resume@plt>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14d3dc:	48 89 c7             	mov    %rax,%rdi
  14d3df:	e8 bc 99 f5 ff       	call   a6da0 <__clang_call_terminate>
  14d3e4:	48 89 c7             	mov    %rax,%rdi
  14d3e7:	e8 b4 99 f5 ff       	call   a6da0 <__clang_call_terminate>
MultiSteersOdometer::CalOdoCoef():
  14d3ec:	49 89 c7             	mov    %rax,%r15
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::__shared_count(std::__shared_count<(__gnu_cxx::_Lock_policy)2> const&):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:690
  14d3ef:	4d 85 e4             	test   %r12,%r12
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14d3f2:	0f 84 d6 00 00 00    	je     14d4ce <MultiSteersOdometer::CalOdoCoef()+0xade>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14d3f8:	48 83 3d a8 a6 2b 00 	cmpq   $0x0,0x2ba6a8(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14d3ff:	00 
  14d400:	74 16                	je     14d418 <MultiSteersOdometer::CalOdoCoef()+0xa28>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14d402:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14d407:	f0 41 0f c1 44 24 08 	lock xadd %eax,0x8(%r12)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14d40e:	83 f8 01             	cmp    $0x1,%eax
  14d411:	74 1b                	je     14d42e <MultiSteersOdometer::CalOdoCoef()+0xa3e>
  14d413:	e9 b6 00 00 00       	jmp    14d4ce <MultiSteersOdometer::CalOdoCoef()+0xade>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14d418:	41 8b 44 24 08       	mov    0x8(%r12),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14d41d:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14d420:	41 89 4c 24 08       	mov    %ecx,0x8(%r12)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14d425:	83 f8 01             	cmp    $0x1,%eax
  14d428:	0f 85 a0 00 00 00    	jne    14d4ce <MultiSteersOdometer::CalOdoCoef()+0xade>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14d42e:	49 8b 04 24          	mov    (%r12),%rax
  14d432:	4c 89 e7             	mov    %r12,%rdi
  14d435:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14d438:	48 83 3d 68 a6 2b 00 	cmpq   $0x0,0x2ba668(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14d43f:	00 
  14d440:	74 13                	je     14d455 <MultiSteersOdometer::CalOdoCoef()+0xa65>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14d442:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14d447:	f0 41 0f c1 44 24 0c 	lock xadd %eax,0xc(%r12)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14d44e:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14d451:	74 14                	je     14d467 <MultiSteersOdometer::CalOdoCoef()+0xa77>
  14d453:	eb 79                	jmp    14d4ce <MultiSteersOdometer::CalOdoCoef()+0xade>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14d455:	41 8b 44 24 0c       	mov    0xc(%r12),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14d45a:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14d45d:	41 89 4c 24 0c       	mov    %ecx,0xc(%r12)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14d462:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14d465:	75 67                	jne    14d4ce <MultiSteersOdometer::CalOdoCoef()+0xade>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14d467:	49 8b 04 24          	mov    (%r12),%rax
  14d46b:	4c 89 e7             	mov    %r12,%rdi
  14d46e:	ff 50 18             	call   *0x18(%rax)
  14d471:	eb 5b                	jmp    14d4ce <MultiSteersOdometer::CalOdoCoef()+0xade>
MultiSteersOdometer::CalOdoCoef():
  14d473:	49 89 c7             	mov    %rax,%r15
  14d476:	e9 c1 00 00 00       	jmp    14d53c <MultiSteersOdometer::CalOdoCoef()+0xb4c>
  14d47b:	49 89 c7             	mov    %rax,%r15
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d47e:	4c 39 f3             	cmp    %r14,%rbx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d481:	0f 84 ce 00 00 00    	je     14d555 <MultiSteersOdometer::CalOdoCoef()+0xb65>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d487:	48 89 df             	mov    %rbx,%rdi
  14d48a:	e8 a1 75 f3 ff       	call   84a30 <operator delete(void*)@plt>
  14d48f:	e9 c1 00 00 00       	jmp    14d555 <MultiSteersOdometer::CalOdoCoef()+0xb65>
MultiSteersOdometer::CalOdoCoef():
  14d494:	49 89 c7             	mov    %rax,%r15
  14d497:	e9 c8 00 00 00       	jmp    14d564 <MultiSteersOdometer::CalOdoCoef()+0xb74>
  14d49c:	49 89 c7             	mov    %rax,%r15
  14d49f:	e9 da 00 00 00       	jmp    14d57e <MultiSteersOdometer::CalOdoCoef()+0xb8e>
  14d4a4:	49 89 c7             	mov    %rax,%r15
  14d4a7:	e9 d2 00 00 00       	jmp    14d57e <MultiSteersOdometer::CalOdoCoef()+0xb8e>
  14d4ac:	49 89 c7             	mov    %rax,%r15
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14d4af:	48 8b 8c 24 a0 00 00 	mov    0xa0(%rsp),%rcx
  14d4b6:	00 
  14d4b7:	48 85 c9             	test   %rcx,%rcx
  14d4ba:	74 12                	je     14d4ce <MultiSteersOdometer::CalOdoCoef()+0xade>
MultiSteersOdometer::CalOdoCoef():
  14d4bc:	48 8d bc 24 90 00 00 	lea    0x90(%rsp),%rdi
  14d4c3:	00 
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14d4c4:	ba 03 00 00 00       	mov    $0x3,%edx
  14d4c9:	48 89 fe             	mov    %rdi,%rsi
  14d4cc:	ff d1                	call   *%rcx
std::__shared_count<(__gnu_cxx::_Lock_policy)2>::~__shared_count():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:683
  14d4ce:	48 8b 5c 24 48       	mov    0x48(%rsp),%rbx
  14d4d3:	48 85 db             	test   %rbx,%rbx
  14d4d6:	74 64                	je     14d53c <MultiSteersOdometer::CalOdoCoef()+0xb4c>
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14d4d8:	48 83 3d c8 a5 2b 00 	cmpq   $0x0,0x2ba5c8(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14d4df:	00 
  14d4e0:	74 11                	je     14d4f3 <MultiSteersOdometer::CalOdoCoef()+0xb03>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14d4e2:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14d4e7:	f0 0f c1 43 08       	lock xadd %eax,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14d4ec:	83 f8 01             	cmp    $0x1,%eax
  14d4ef:	74 10                	je     14d501 <MultiSteersOdometer::CalOdoCoef()+0xb11>
  14d4f1:	eb 49                	jmp    14d53c <MultiSteersOdometer::CalOdoCoef()+0xb4c>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14d4f3:	8b 43 08             	mov    0x8(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14d4f6:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14d4f9:	89 4b 08             	mov    %ecx,0x8(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:151
  14d4fc:	83 f8 01             	cmp    $0x1,%eax
  14d4ff:	75 3b                	jne    14d53c <MultiSteersOdometer::CalOdoCoef()+0xb4c>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:154
  14d501:	48 8b 03             	mov    (%rbx),%rax
  14d504:	48 89 df             	mov    %rbx,%rdi
  14d507:	ff 50 10             	call   *0x10(%rax)
__gnu_cxx::__exchange_and_add_dispatch(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:81
  14d50a:	48 83 3d 96 a5 2b 00 	cmpq   $0x0,0x2ba596(%rip)        # 407aa8 <__pthread_key_create@GLIBC_2.2.5>
  14d511:	00 
  14d512:	74 11                	je     14d525 <MultiSteersOdometer::CalOdoCoef()+0xb35>
__gnu_cxx::__exchange_and_add(int volatile*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:49
  14d514:	b8 ff ff ff ff       	mov    $0xffffffff,%eax
  14d519:	f0 0f c1 43 0c       	lock xadd %eax,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14d51e:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14d521:	74 10                	je     14d533 <MultiSteersOdometer::CalOdoCoef()+0xb43>
  14d523:	eb 17                	jmp    14d53c <MultiSteersOdometer::CalOdoCoef()+0xb4c>
__gnu_cxx::__exchange_and_add_single(int*, int):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:67
  14d525:	8b 43 0c             	mov    0xc(%rbx),%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/atomicity.h:68
  14d528:	8d 48 ff             	lea    -0x1(%rax),%ecx
  14d52b:	89 4b 0c             	mov    %ecx,0xc(%rbx)
std::_Sp_counted_base<(__gnu_cxx::_Lock_policy)2>::_M_release():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:167
  14d52e:	83 f8 01             	cmp    $0x1,%eax
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:166
  14d531:	75 09                	jne    14d53c <MultiSteersOdometer::CalOdoCoef()+0xb4c>
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/shared_ptr_base.h:170
  14d533:	48 8b 03             	mov    (%rbx),%rax
  14d536:	48 89 df             	mov    %rbx,%rdi
  14d539:	ff 50 18             	call   *0x18(%rax)
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:275
  14d53c:	48 8b 4c 24 60       	mov    0x60(%rsp),%rcx
  14d541:	48 85 c9             	test   %rcx,%rcx
  14d544:	74 0f                	je     14d555 <MultiSteersOdometer::CalOdoCoef()+0xb65>
MultiSteersOdometer::CalOdoCoef():
  14d546:	48 8d 7c 24 50       	lea    0x50(%rsp),%rdi
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14d54b:	ba 03 00 00 00       	mov    $0x3,%edx
  14d550:	48 89 fe             	mov    %rdi,%rsi
  14d553:	ff d1                	call   *%rcx
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d555:	48 8b 7c 24 70       	mov    0x70(%rsp),%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d55a:	4c 39 ef             	cmp    %r13,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d55d:	74 05                	je     14d564 <MultiSteersOdometer::CalOdoCoef()+0xb74>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d55f:	e8 cc 74 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d564:	48 8b bc 24 c8 00 00 	mov    0xc8(%rsp),%rdi
  14d56b:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14d56c:	48 8d 84 24 d8 00 00 	lea    0xd8(%rsp),%rax
  14d573:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d574:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d577:	74 05                	je     14d57e <MultiSteersOdometer::CalOdoCoef()+0xb8e>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d579:	e8 b2 74 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >::~basic_stringstream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/sstream:731
  14d57e:	48 8b 1d e3 a4 2b 00 	mov    0x2ba4e3(%rip),%rbx        # 407a68 <VTT for std::__cxx11::basic_stringstream<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  14d585:	48 8b 03             	mov    (%rbx),%rax
  14d588:	48 89 84 24 f8 00 00 	mov    %rax,0xf8(%rsp)
  14d58f:	00 
  14d590:	48 8b 4b 40          	mov    0x40(%rbx),%rcx
  14d594:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14d598:	48 89 8c 04 f8 00 00 	mov    %rcx,0xf8(%rsp,%rax,1)
  14d59f:	00 
  14d5a0:	48 8b 43 48          	mov    0x48(%rbx),%rax
  14d5a4:	48 89 84 24 08 01 00 	mov    %rax,0x108(%rsp)
  14d5ab:	00 
std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >::~basic_stringbuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/sstream.tcc:291
  14d5ac:	48 8b 05 b5 98 2b 00 	mov    0x2b98b5(%rip),%rax        # 406e68 <vtable for std::__cxx11::basic_stringbuf<char, std::char_traits<char>, std::allocator<char> >@GLIBCXX_3.4.21>
  14d5b3:	48 83 c0 10          	add    $0x10,%rax
  14d5b7:	48 89 84 24 10 01 00 	mov    %rax,0x110(%rsp)
  14d5be:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d5bf:	48 8b bc 24 58 01 00 	mov    0x158(%rsp),%rdi
  14d5c6:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_local_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:192
  14d5c7:	48 8d 84 24 68 01 00 	lea    0x168(%rsp),%rax
  14d5ce:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d5cf:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d5d2:	74 05                	je     14d5d9 <MultiSteersOdometer::CalOdoCoef()+0xbe9>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d5d4:	e8 57 74 f3 ff       	call   84a30 <operator delete(void*)@plt>
std::basic_streambuf<char, std::char_traits<char> >::~basic_streambuf():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/streambuf:198
  14d5d9:	48 8b 05 38 a3 2b 00 	mov    0x2ba338(%rip),%rax        # 407918 <vtable for std::basic_streambuf<char, std::char_traits<char> >@GLIBCXX_3.4>
  14d5e0:	48 83 c0 10          	add    $0x10,%rax
  14d5e4:	48 89 84 24 10 01 00 	mov    %rax,0x110(%rsp)
  14d5eb:	00 
  14d5ec:	48 8d bc 24 48 01 00 	lea    0x148(%rsp),%rdi
  14d5f3:	00 
  14d5f4:	e8 37 8c f3 ff       	call   86230 <std::locale::~locale()@plt>
std::basic_istream<char, std::char_traits<char> >::~basic_istream():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/istream:104
  14d5f9:	48 8b 43 10          	mov    0x10(%rbx),%rax
  14d5fd:	48 8b 4b 18          	mov    0x18(%rbx),%rcx
  14d601:	48 89 84 24 f8 00 00 	mov    %rax,0xf8(%rsp)
  14d608:	00 
  14d609:	48 8b 40 e8          	mov    -0x18(%rax),%rax
  14d60d:	48 89 8c 04 f8 00 00 	mov    %rcx,0xf8(%rsp,%rax,1)
  14d614:	00 
  14d615:	48 c7 84 24 00 01 00 	movq   $0x0,0x100(%rsp)
  14d61c:	00 00 00 00 00 
std::basic_ios<char, std::char_traits<char> >::~basic_ios():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_ios.h:282
  14d621:	48 8d bc 24 78 01 00 	lea    0x178(%rsp),%rdi
  14d628:	00 
  14d629:	e8 f2 7c f3 ff       	call   85320 <std::ios_base::~ios_base()@plt>
  14d62e:	4c 89 ff             	mov    %r15,%rdi
  14d631:	e8 4a 79 f3 ff       	call   84f80 <_Unwind_Resume@plt>
std::_Function_base::~_Function_base():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/std_function.h:276
  14d636:	48 89 c7             	mov    %rax,%rdi
  14d639:	e8 62 97 f5 ff       	call   a6da0 <__clang_call_terminate>
  14d63e:	48 89 c7             	mov    %rax,%rdi
  14d641:	e8 5a 97 f5 ff       	call   a6da0 <__clang_call_terminate>
MultiSteersOdometer::CalOdoCoef():
  14d646:	49 89 c7             	mov    %rax,%r15
  14d649:	48 8d bc 24 f8 00 00 	lea    0xf8(%rsp),%rdi
  14d650:	00 
/root/workspace/3.4.5.20/plugins/OdoCalculator/src/Odometer/multisteerodometer.cpp:104
  14d651:	e8 9a 7f f3 ff       	call   855f0 <std::basic_ofstream<char, std::char_traits<char> >::~basic_ofstream()@plt>
  14d656:	4c 89 ff             	mov    %r15,%rdi
  14d659:	e8 22 79 f3 ff       	call   84f80 <_Unwind_Resume@plt>
  14d65e:	49 89 c7             	mov    %rax,%r15
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_data() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:176
  14d661:	48 8b bc 24 f8 00 00 	mov    0xf8(%rsp),%rdi
  14d668:	00 
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_is_local() const:
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:211
  14d669:	48 8d 84 24 08 01 00 	lea    0x108(%rsp),%rax
  14d670:	00 
  14d671:	48 39 c7             	cmp    %rax,%rdi
std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose():
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/bits/basic_string.h:220
  14d674:	75 08                	jne    14d67e <MultiSteersOdometer::CalOdoCoef()+0xc8e>
MultiSteersOdometer::CalOdoCoef():
  14d676:	4c 89 ff             	mov    %r15,%rdi
  14d679:	e8 02 79 f3 ff       	call   84f80 <_Unwind_Resume@plt>
__gnu_cxx::new_allocator<char>::deallocate(char*, unsigned long):
/usr/bin/../lib/gcc/x86_64-linux-gnu/7.5.0/../../../../include/c++/7.5.0/ext/new_allocator.h:125
  14d67e:	e8 ad 73 f3 ff       	call   84a30 <operator delete(void*)@plt>
MultiSteersOdometer::CalOdoCoef():
  14d683:	4c 89 ff             	mov    %r15,%rdi
  14d686:	e8 f5 78 f3 ff       	call   84f80 <_Unwind_Resume@plt>
  14d68b:	0f 1f 44 00 00       	nopl   0x0(%rax,%rax,1)
