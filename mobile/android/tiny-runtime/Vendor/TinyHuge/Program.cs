using Mono.Cecil;using Mono.Cecil.Cil;
using var assembly=AssemblyDefinition.ReadAssembly(args[0]);
assembly.Name.Name="BoardLens.TinyHuge";assembly.MainModule.Name="BoardLens.TinyHuge.dll";
assembly.MainModule.Mvid=new Guid("b802c4f1-08dc-48ef-a794-bd1430aa6c40");
foreach(var reference in assembly.MainModule.AssemblyReferences){if(reference.Name=="Chess-Challenge")reference.Name="BoardLens.Android";if(reference.Name=="System.Runtime"){reference.Version=new Version(10,0,0,0);reference.PublicKeyToken=Convert.FromHexString("b03f5f7f11d50a3a");}}
// The challenge compressor also encoded primitive/value-type signatures as
// class references. CoreCLR tolerates these; Mono requires normal ECMA signatures.
TypeReference Normal(TypeReference t){
 if(t is ArrayType a)return new ArrayType(Normal(a.ElementType),a.Rank);
 if(t is ByReferenceType b)return new ByReferenceType(Normal(b.ElementType));
 if(t is PointerType p)return new PointerType(Normal(p.ElementType));
 if(t is GenericInstanceType g){var r=new GenericInstanceType(Normal(g.ElementType));foreach(var arg in g.GenericArguments)r.GenericArguments.Add(Normal(arg));return r;}
 var ts=assembly.MainModule.TypeSystem;
 var primitive=t.FullName switch {"System.Boolean"=>ts.Boolean,"System.Byte"=>ts.Byte,"System.SByte"=>ts.SByte,"System.Int16"=>ts.Int16,"System.UInt16"=>ts.UInt16,"System.Int32"=>ts.Int32,"System.UInt32"=>ts.UInt32,"System.Int64"=>ts.Int64,"System.UInt64"=>ts.UInt64,"System.Char"=>ts.Char,"System.Single"=>ts.Single,"System.Double"=>ts.Double,"System.IntPtr"=>ts.IntPtr,"System.UIntPtr"=>ts.UIntPtr,"System.Void"=>ts.Void,_=>null};
 if(primitive!=null)return primitive;
 if(t.FullName is "ChessChallenge.API.Move" or "ChessChallenge.API.Square" or "ChessChallenge.API.PieceType" or "System.Span`1" or "System.RuntimeFieldHandle")t.IsValueType=true;
 return t;
}
foreach(var type in assembly.MainModule.Types){
 foreach(var field in type.Fields)field.FieldType=Normal(field.FieldType);
 foreach(var method in type.Methods){method.ReturnType=Normal(method.ReturnType);foreach(var parameter in method.Parameters)parameter.ParameterType=Normal(parameter.ParameterType);
 if(!method.HasBody)continue;foreach(var variable in method.Body.Variables)variable.VariableType=Normal(variable.VariableType);
 foreach(var instruction in method.Body.Instructions){
  if(instruction.Operand is TypeReference t)instruction.Operand=Normal(t);
  if(instruction.Operand is FieldReference f){f.FieldType=Normal(f.FieldType);f.DeclaringType=Normal(f.DeclaringType);}
  if(instruction.Operand is MethodReference m){m.ReturnType=Normal(m.ReturnType);m.DeclaringType=Normal(m.DeclaringType);foreach(var parameter in m.Parameters)parameter.ParameterType=Normal(parameter.ParameterType);}
 }
 }
}
int capped=0;
foreach(var type in assembly.MainModule.Types){
 int fieldId=0,methodId=0;foreach(var field in type.Fields)if(string.IsNullOrWhiteSpace(field.Name))field.Name="field"+(fieldId++);
 if(type.Name=="e")type.IsPublic=true;
 foreach(var method in type.Methods){if(string.IsNullOrWhiteSpace(method.Name))method.Name="method"+(methodId++);int p=0;foreach(var parameter in method.Parameters)parameter.Name="arg"+(p++);
 if(type.Name=="e"&&method.IsConstructor)method.IsPublic=true;
 if(method.HasBody)foreach(var instruction in method.Body.Instructions)if(instruction.OpCode==OpCodes.Ldc_I4&&instruction.Operand is int n&&n==25165824){instruction.Operand=262144;capped++;}}
}
// Materialize primitive arrays with normal stores. The original compressed
// RVA field handles are accepted by CoreCLR but rejected by Android Mono.
int initialized=0;
foreach(var type in assembly.MainModule.Types)foreach(var method in type.Methods){
 if(!method.HasBody)continue;
 foreach(var call in method.Body.Instructions.ToArray()){
  if(call.Operand is not MethodReference target||target.DeclaringType.FullName!="System.Runtime.CompilerServices.RuntimeHelpers"||target.Name!="InitializeArray")continue;
  var token=call.Previous;var duplicate=token.Previous;var create=duplicate.Previous;var length=create.Previous;
  if(token.OpCode!=OpCodes.Ldtoken||duplicate.OpCode!=OpCodes.Dup||create.OpCode!=OpCodes.Newarr)throw new Exception("Unexpected array initializer");
  int count=length.OpCode.Code switch {Code.Ldc_I4=>(int)length.Operand,Code.Ldc_I4_S=>(sbyte)length.Operand,Code.Ldc_I4_0=>0,Code.Ldc_I4_1=>1,Code.Ldc_I4_2=>2,Code.Ldc_I4_3=>3,Code.Ldc_I4_4=>4,Code.Ldc_I4_5=>5,Code.Ldc_I4_6=>6,Code.Ldc_I4_7=>7,Code.Ldc_I4_8=>8,_=>throw new Exception("Array length")};
  var field=((FieldReference)token.Operand).Resolve();var data=field.InitialValue;var element=(TypeReference)create.Operand;
  int width=element.MetadataType switch {MetadataType.Byte or MetadataType.SByte=>1,MetadataType.Int16 or MetadataType.UInt16=>2,MetadataType.Int32 or MetadataType.UInt32=>4,MetadataType.Int64 or MetadataType.UInt64=>8,_=>throw new Exception("Non-primitive initializer")};
  if(data.Length<count*width)throw new Exception("Initializer data too short");
  duplicate.OpCode=OpCodes.Nop;duplicate.Operand=null;token.OpCode=OpCodes.Nop;token.Operand=null;call.OpCode=OpCodes.Nop;call.Operand=null;
  var il=method.Body.GetILProcessor();for(int i=0;i<count;i++){
   il.InsertBefore(call,Instruction.Create(OpCodes.Dup));il.InsertBefore(call,Instruction.Create(OpCodes.Ldc_I4,i));
   if(width==8)il.InsertBefore(call,Instruction.Create(OpCodes.Ldc_I8,BitConverter.ToInt64(data,i*8)));
   else il.InsertBefore(call,Instruction.Create(OpCodes.Ldc_I4,width==1?data[i]:width==2?(int)BitConverter.ToInt16(data,i*2):BitConverter.ToInt32(data,i*4)));
   il.InsertBefore(call,Instruction.Create(width==1?OpCodes.Stelem_I1:width==2?OpCodes.Stelem_I2:width==4?OpCodes.Stelem_I4:OpCodes.Stelem_I8));
  }initialized++;
 }
}
Console.WriteLine("Primitive array initializers normalized: "+initialized);
if(capped!=4)throw new Exception("Unexpected TinyHugeBot table operands");
assembly.Write(args[1]);Console.WriteLine("Packaged TinyHugeBot with valid GUID metadata and bounded hash tables");
