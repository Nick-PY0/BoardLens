// TinyHugeBot, Popax21 and atpx8. MIT challenge submission.
// Decompiled from the verified submitted payload for normal Android compilation.
// Reproduction and adaptations: ../Vendor/TinyHuge/README.md.
using System;
using System.Numerics;
using System.Reflection;
using System.Runtime.InteropServices;
using ChessChallenge.API;
using Timer=ChessChallenge.API.Timer;

namespace auto_Bot_610_original;

internal static class Tables
{
	internal static readonly int[] field0;

	internal static ulong[] field1;

	internal static ushort[] field2;

	internal static short[] field3;

	internal static short[] field4;

	internal static int[] field5;

	internal static readonly ulong[] field6;

	internal static readonly ulong[] field7;

	internal static readonly ulong[] field8;

	internal static readonly sbyte[] field9;









	public static int method0(Board arg0, Move arg1, bool arg2)
	{
		int index = arg1.TargetSquare.Index;
		ulong num = (ulong)(1L << index);
		ulong num2 = arg0.AllPiecesBitboard;
		Span<ulong> span = stackalloc ulong[12];
		for (int i = 0; i < 12; i++)
		{
			span[i] = arg0.GetPieceBitboard((PieceType)(i / 2 + 1), i % 2 == 0);
		}
		ulong num3 = 0uL;
		num3 |= span[0] & (((num & 0xFEFEFEFEFEFEFEFEuL) >> 9) | ((num & 0x7F7F7F7F7F7F7F7FL) >> 7));
		num3 |= span[1] & (((num & 0xFEFEFEFEFEFEFEFEuL) << 7) | ((num & 0x7F7F7F7F7F7F7F7FL) << 9));
		num3 |= (span[2] | span[3]) & field7[index];
		ulong num4 = span[6] | span[7] | span[8] | span[9];
		ulong num5 = method2(index, num2, 0);
		ulong num6 = method1(index, num2, 1);
		ulong num7 = method2(index, num2, 2);
		ulong num8 = method1(index, num2, 3);
		num3 |= num4 & (num5 | num6 | num7 | num8);
		ulong num9 = span[4] | span[5] | span[8] | span[9];
		ulong num10 = method2(index, num2, 4);
		ulong num11 = method1(index, num2, 5);
		ulong num12 = method2(index, num2, 6);
		ulong num13 = method1(index, num2, 7);
		num3 |= num9 & (num10 | num11 | num12 | num13);
		num3 |= (span[10] | span[11]) & field6[index];
		int num14 = 0;
		Span<int> span2 = stackalloc int[32];
		span2[0] = field5[(int)(arg1.CapturePieceType - 1)];
		ulong num15 = num2 ^ span[2] ^ span[3] ^ span[10] ^ span[11];
		int num16 = (int)(arg1.MovePieceType - 1);
		int num17 = ((!arg2) ? 1 : 0);
		ulong num18 = (ulong)(1L << arg1.StartSquare.Index);
		do
		{
			num14++;
			span2[num14] = field5[num16] - span2[num14 - 1];
			if (span2[num14] < 0 && span2[num14 - 1] > 0)
			{
				break;
			}
			num3 ^= num18;
			num2 ^= num18;
			num17 ^= 1;
			if ((num18 & num15) != 0L)
			{
				if ((num18 & num5) != 0L)
				{
					num5 = method2(index, num2, 0);
				}
				else if ((num18 & num6) != 0L)
				{
					num6 = method1(index, num2, 1);
				}
				else if ((num18 & num7) != 0L)
				{
					num7 = method2(index, num2, 2);
				}
				else if ((num18 & num8) != 0L)
				{
					num8 = method1(index, num2, 3);
				}
				else if ((num18 & num10) != 0L)
				{
					num10 = method2(index, num2, 4);
				}
				else if ((num18 & num11) != 0L)
				{
					num11 = method1(index, num2, 5);
				}
				else if ((num18 & num12) != 0L)
				{
					num12 = method2(index, num2, 6);
				}
				else if ((num18 & num13) != 0L)
				{
					num13 = method1(index, num2, 7);
				}
				num3 |= num2 & num4 & (num5 | num6 | num7 | num8);
				num3 |= num2 & num9 & (num10 | num11 | num12 | num13);
			}
			num18 = 0uL;
			for (int j = num17; j < 12; j += 2)
			{
				ulong num19 = span[j] & num3;
				if (num19 != 0L)
				{
					num16 = j / 2;
					num18 = num19 & ~(num19 - 1);
					break;
				}
			}
		}
		while (num18 != 0L);
		while (--num14 > 0)
		{
			if (-span2[num14] < span2[num14 - 1])
			{
				span2[num14 - 1] = -span2[num14];
			}
		}
		return span2[0];
	}

	internal static ulong method1(int arg0, ulong arg1, int arg2)
	{
		ulong num = field8[arg2 * 65 + arg0];
		int num2 = BitOperations.TrailingZeroCount(num & arg1);
		return num ^ field8[arg2 * 65 + num2];
	}

	internal static ulong method2(int arg0, ulong arg1, int arg2)
	{
		ulong num = field8[arg2 * 65 + arg0];
		int num2 = 63 - BitOperations.LeadingZeroCount((num & arg1) | 1);
		return num ^ field8[arg2 * 65 + num2];
	}

	static Tables()
	{
		field0 = new int[6] { 0, 1, 1, 2, 4, 0 };
		field1 = new ulong[768];
		field2 = new ushort[397]
		{
			65501, 65528, 2083, 2083, 2083, 2083, 2083, 2083, 2083, 2083,
			5376, 4130, 4111, 4620, 5396, 2107, 2633, 269, 3081, 3871,
			543, 2329, 2086, 806, 1860, 23, 5384, 4385, 1310, 303,
			308, 41, 2861, 1802, 10261, 8240, 5417, 3384, 1594, 3119,
			6452, 6412, 26141, 27690, 23869, 19266, 16484, 15707, 23100, 23567,
			47749, 46505, 42592, 36482, 39783, 36001, 44357, 49944, 2083, 2083,
			2083, 2083, 2083, 2083, 2083, 2083, 65369, 65437, 17982, 12434,
			19565, 21638, 19862, 20875, 12692, 9104, 14730, 20338, 22939, 24228,
			24998, 20409, 19609, 14228, 19600, 24734, 25267, 29361, 28090, 24760,
			20416, 19863, 20890, 23979, 29623, 31924, 29635, 29882, 26556, 20895,
			21150, 26296, 31162, 31196, 31180, 28396, 27577, 20925, 19320, 20451,
			28108, 27880, 25339, 23080, 20720, 15059, 19038, 23422, 19183, 25035,
			23230, 19173, 19374, 12182, 10496, 15694, 22149, 18294, 17636, 18502,
			9368, 60, 65454, 65509, 1073, 4687, 1092, 5693, 4677, 2886,
			5675, 2621, 3414, 2401, 5218, 6738, 8025, 4711, 3187, 83,
			3922, 6241, 9057, 9569, 10336, 7789, 5220, 3164, 5452, 7775,
			10335, 11884, 8820, 9566, 6236, 4694, 6222, 9303, 10085, 9348,
			10615, 9591, 7769, 7504, 7490, 4983, 7037, 6778, 6517, 8580,
			7031, 8016, 4920, 5986, 8768, 3909, 6256, 3725, 5988, 3363,
			3381, 1622, 4096, 4909, 5177, 4648, 2649, 842, 65465, 65516,
			2868, 5690, 5960, 4952, 3927, 1870, 6178, 45, 3611, 3639,
			5171, 5694, 2886, 2898, 2369, 4352, 4122, 5166, 3895, 4918,
			3402, 2119, 3138, 1062, 5923, 6445, 7227, 6214, 3920, 3648,
			3149, 2352, 6191, 5948, 8526, 5473, 5727, 5482, 4927, 5683,
			6978, 7002, 7009, 6507, 6232, 4468, 3972, 4439, 8034, 8551,
			8577, 8069, 4503, 6026, 7265, 6003, 8551, 7793, 9831, 9082,
			8326, 8272, 7270, 6514, 65486, 65493, 2609, 3872, 5417, 60,
			9763, 2841, 5907, 512, 5391, 5162, 3389, 6964, 6970, 5185,
			1839, 2867, 6948, 4148, 14887, 12592, 13357, 15412, 13632, 12343,
			6441, 18200, 15913, 23080, 18992, 19758, 21045, 16943, 11799, 16663,
			17186, 22562, 25649, 21315, 25648, 20275, 5925, 12577, 13369, 23610,
			23119, 20074, 15969, 13419, 6682, 16139, 19245, 21555, 25890, 17515,
			18766, 11112, 8726, 16690, 16719, 17982, 18029, 15966, 13661, 16223,
			65471, 65462, 5426, 10341, 13645, 16139, 11849, 15397, 12889, 8015,
			12098, 16200, 20025, 22273, 22550, 20017, 17738, 14665, 14131, 18227,
			21803, 24339, 24853, 23075, 20786, 16678, 14352, 17984, 24358, 25114,
			25875, 24853, 21280, 16142, 16944, 24621, 25141, 25894, 25635, 27432,
			25651, 19741, 21560, 23385, 24899, 22833, 24109, 30535, 30295, 22315,
			15966, 23360, 22573, 23354, 23353, 28733, 24859, 21796, 0, 10072,
			14417, 14386, 16137, 22815, 20035, 14670, 1133
		};
		field3 = new short[6] { 82, 337, 365, 477, 1025, 0 };
		field4 = new short[6] { 94, 281, 297, 512, 936, 0 };
		uint[] array = new uint[384];
		for (int i = 0; i < 6; i++)
		{
			short num = (short)field2[i * 66];
			short num2 = (short)field2[i * 66 + 1];
			for (int j = 0; j < 64; j++)
			{
				ushort num3 = field2[i * 66 + 2 + j];
				short num4 = (short)(num + (byte)(num3 & 0xFF));
				short num5 = (short)(num2 + (byte)(num3 >> 8));
				array[(i << 6) | j] = (uint)(((ushort)num5 << 16) | (ushort)num4);
			}
		}
		for (int k = 396; k < field2.Length; k++)
		{
			uint num6 = field2[k];
			ref uint reference = ref array[num6 & 0x1FF];
			short num7 = (short)(reference & 0xFFFF);
			short num8 = (short)(reference >> 16);
			num7 += (short)(((num6 >> 10) & 7) << 8);
			num8 += (short)(((num6 >> 13) & 7) << 8);
			reference = (uint)(((ushort)num8 << 16) | (ushort)num7);
		}
		for (int l = 0; l < 6; l++)
		{
			for (int m = 0; m < 64; m++)
			{
				short num9 = (short)(field3[l] + (short)(array[(l << 6) | m] & 0xFFFF));
				short num10 = (short)(field4[l] + (short)(array[(l << 6) | m] >> 16));
				field1[(l << 6) | m] = ((ulong)(ushort)num10 << 32) | (ushort)num9;
				field1[(l + 6 << 6) | (m ^ 0x38)] = ((ulong)(ushort)(short)(-num10) << 32) | (ushort)(short)(-num9);
			}
		}
		field5 = new int[6] { 1, 12, 14, 22, 40, 10000 };
		field6 = new ulong[64];
		field7 = new ulong[64];
		field8 = new ulong[520];
		field9 = new sbyte[8] { -1, 1, -8, 8, -9, 9, -7, 7 };
		for (int n = 0; n < 64; n++)
		{
			ulong num11 = (ulong)(1L << n);
			field6[n] |= num11 << 8;
			field6[n] |= num11 >> 8;
			field6[n] |= (num11 & 0xFEFEFEFEFEFEFEFEuL) << 7;
			field6[n] |= (num11 & 0xFEFEFEFEFEFEFEFEuL) >> 1;
			field6[n] |= (num11 & 0xFEFEFEFEFEFEFEFEuL) >> 9;
			field6[n] |= (num11 & 0x7F7F7F7F7F7F7F7FL) << 9;
			field6[n] |= (num11 & 0x7F7F7F7F7F7F7F7FL) << 1;
			field6[n] |= (num11 & 0x7F7F7F7F7F7F7F7FL) >> 7;
			field7[n] |= ((num11 & 0xFEFEFEFEFEFEFEFEuL) << 15) | ((num11 & 0xFEFEFEFEFEFEFEFEuL) >> 17);
			field7[n] |= ((num11 & 0x7F7F7F7F7F7F7F7FL) << 17) | ((num11 & 0x7F7F7F7F7F7F7F7FL) >> 15);
			field7[n] |= ((num11 & 0xFCFCFCFCFCFCFCFCuL) << 6) | ((num11 & 0xFCFCFCFCFCFCFCFCuL) >> 10);
			field7[n] |= ((num11 & 0x3F3F3F3F3F3F3F3FL) << 10) | ((num11 & 0x3F3F3F3F3F3F3F3FL) >> 6);
			for (int num12 = 0; num12 < 8; num12++)
			{
				int num13 = field9[num12];
				ulong num14 = (num13 & 7) switch
				{
					0 => ulong.MaxValue, 
					1 => 9187201950435737471uL, 
					7 => 18374403900871474942uL, 
					_ => 0uL, 
				};
				ulong num15 = num11;
				while (true)
				{
					num15 &= num14;
					num15 = ((num13 < 0) ? (num15 >> -num13) : (num15 << num13));
					if (num15 == 0L)
					{
						break;
					}
					field8[num12 * 65 + n] |= num15;
				}
			}
		}
	}
}
public class Search : IChessBot
{
	internal Board field0;

	internal EvaluationState field1;

	internal Timer field2;

	internal int field3;

	internal ushort[] field4 = new ushort[1024];

	internal uint[] field5 = new uint[1024];

	internal uint[] field6 = new uint[1048576];

	internal uint[] field7 = new uint[1048576];

	internal uint[] field8 = new uint[1024];

	internal int[] field9 = new int[256];

	internal int[] field10 = new int[256];

	internal int field11;

	internal ushort[] field12 = new ushort[256];

	internal static byte[] field13 = new byte[5] { 0, 7, 8, 17, 49 };

	internal static readonly ushort[] field14 = new ushort[7] { 1180, 270, 490, 520, 680, 1180, 0 };

	internal ulong[] field15 = new ulong[BoardLens.Mobile.TinyMemory.HashEntries];

	internal ushort[] field16 = new ushort[BoardLens.Mobile.TinyMemory.HashEntries];

	public Move Think(Board arg0, Timer arg1)
	{
		field0 = arg0;
		field2 = arg1;
		field3 = arg1.MillisecondsRemaining / 30;
		int num = arg1.MillisecondsRemaining / 38;
		ulong num2 = 9223372039002259456uL;
		int num3 = 0;
		for (int i = 0; i <= 6; i += 6)
		{
			for (int j = 0; j < 6; j++)
			{
				for (ulong num4 = arg0.GetPieceBitboard((PieceType)(j + 1), i == 0); num4 != 0L; num4 &= num4 - 1)
				{
					num2 += Tables.field1[(j + i << 6) | BitOperations.TrailingZeroCount(num4)];
					num3 += Tables.field0[j];
				}
			}
		}
		field1 = new EvaluationState
		{
			field0 = arg0.IsWhiteToMove,
			field2 = num2,
			field1 = num3
		};
		Array.Fill(field4, (ushort)0);
		Array.Fill(field5, 0u);
		Array.Fill(field6, 0u);
		Array.Fill(field7, 0u);
		Array.Fill(field8, 1u);
		Span<Move> moveList = stackalloc Move[256];
		arg0.GetLegalMovesNonAlloc(ref moveList);
		int num5 = 0;
		ushort num6 = 0;
		int num7 = 1;
		while (true)
		{
			ushort arg2 = 0;
			try
			{
				num5 = method1(-1048576, 1048576, num7, 0, ref arg2, 0);
				num6 = arg2;
			}
			catch (Exception)
			{
				if (arg2 != 0)
				{
					num6 = arg2;
				}
			}
			if (arg1.MillisecondsElapsedThisTurn >= num || num5 <= -29000 || num5 >= 29000 || num7 >= 63)
			{
				break;
			}
			num7++;
		}
		int num8 = 0;
		Move result;
		while (true)
		{
			if (num8 < moveList.Length)
			{
				if (moveList[num8].RawValue == num6)
				{
					result = moveList[num8];
					break;
				}
				num8++;
				continue;
			}
			result = default;
			break;
		}
		return result;
	}

	public void method0(Span<Move> arg0, Span<ulong> arg1, int arg2, bool arg3, ushort arg4, bool arg5)
	{
		for (int i = 0; i < arg0.Length; i++)
		{
			Move move = arg0[i];
			if (move.RawValue == arg4)
			{
				arg1[i] = 0uL;
				continue;
			}
			bool flag = !move.IsCapture && !move.IsPromotion;
			if (flag == arg5)
			{
				ref ulong reference = ref arg1[i];
				long num;
				if (!flag)
				{
					num = (long)(((int)move.PromotionPieceType << 6) | ((int)move.CapturePieceType << 3) | (int)(7 - move.MovePieceType)) << 55;
				}
				else
				{
					int num2 = 0;
					while (true)
					{
						if (num2 < 4)
						{
							if (field4[4 * arg2 + num2] == move.RawValue)
							{
								num = (long)(8 - num2) << 52;
								break;
							}
							num2++;
							continue;
						}
						if (field12[arg2] != 0 && ((move.StartSquare.Index == ((field12[arg2] >> 6) & 0x3F)) ? true : false))
						{
							num = 18014398509481984L;
							break;
						}
						int num3 = ((!field0.IsWhiteToMove) ? 512 : 0) | ((int)move.MovePieceType << 6) | move.TargetSquare.Index;
						ulong num4 = field5[num3];
						if (arg2 > 0)
						{
							num4 += field6[(field9[arg2 - 1] << 10) | num3];
						}
						if (arg2 > 1)
						{
							num4 += field7[(field9[arg2 - 2] << 10) | num3];
						}
						num = (long)((num4 << 20) / field8[num3] + 1);
						break;
					}
				}
				reference = (ulong)num;
			}
			else
			{
				arg1[i] = 0uL;
			}
		}
	}

	public int method1(int arg0, int arg1, int arg2, int arg3, ref ushort arg4, int arg5)
	{
		arg4 = 0;
		if (arg2 < 0)
		{
			arg2 = 0;
		}
		if ((++field11 & 0xFFF) == 0 && field2.MillisecondsElapsedThisTurn >= field3)
		{
			throw new Exception();
		}
		bool isWhiteToMove = field0.IsWhiteToMove;
		bool flag = field0.IsInCheck();
		bool flag2 = arg2 <= 0;
		bool flag3 = !flag2 && arg0 + 1 < arg1;
		if (arg3 > 0 && field0.IsRepeatedPosition())
		{
			return 0;
		}
		ulong zobristKey = field0.ZobristKey;
		ulong num = zobristKey % BoardLens.Mobile.TinyMemory.HashEntries;
		ulong num2 = field15[num];
		bool flag4;
		if ((num2 & 0xFFFFFFFFFF000000uL) != (zobristKey & 0xFFFFFFFFFF000000uL))
		{
			flag4 = false;
			if (false)
			{
				goto IL_0131;
			}
		}
		else
		{
			flag4 = true;
			if ((int)((num2 >> 18) & 0x3F) >= arg2 && (int)(num2 & 0x30000) switch
			{
				65536 => true, 
				131072 => arg1 <= (short)num2, 
				196608 => (short)num2 <= arg0, 
				_ => false, 
			})
			{
				goto IL_0131;
			}
		}
		goto IL_0147;
		IL_0147:
		short num3 = (short)num2;
		field12[arg3] = 0;
		int num4 = field1.method0();
		field10[arg3] = num4;
		if (flag4 && -29000 < num3 && num3 < 29000)
		{
			num4 = num3;
		}
		bool flag5 = arg3 >= 2 && num4 > field10[arg3 - 2];
		bool flag6 = false;
		int num5 = -1;
		if (!flag2 && !flag && !flag3 && arg1 > -29000)
		{
			int num6 = 0;
			num6 = num4 - arg2 * 90 - 90;
			if (arg2 < 7 && num6 >= arg1)
			{
				return num6;
			}
			int num7 = 2 + arg2 / 4;
			if (num4 >= arg1 && arg2 > 1)
			{
				num7 = 1 + arg2 * 3 / 8 + (num4 - arg1) / 80;
			}
			field9[arg3] = 0;
			field0.ForceSkipTurn();
			field1.field0 = !field1.field0;
			num6 = -method1(-arg1, -arg1 + 1, arg2 - 1 - num7, arg3 + 1, ref field12[arg3], arg5);
			field0.UndoSkipTurn();
			field1.field0 = !field1.field0;
			if (true)
			{
				if (num6 >= arg1)
				{
					return num6;
				}
				if (arg2 <= 3 && num6 <= -29000 && num4 >= arg1)
				{
					int num8 = arg5;
					arg5++;
					if (arg5 > 6)
					{
						arg5 = 6;
					}
					arg2 += arg5 - num8;
				}
			}
			flag6 = arg2 <= 4 && num4 + 100 * arg2 <= arg0;
			num5 = ((arg2 < 5) ? (field13[arg2] / (flag5 ? 1 : 2)) : (-1));
		}
		if (flag2 && num4 > arg0)
		{
			if (num4 >= arg1)
			{
				return num4;
			}
			arg0 = num4;
		}
		Span<Move> moveList = stackalloc Move[256];
		field0.GetLegalMovesNonAlloc(ref moveList, flag2);
		if (moveList.Length == 0)
		{
			if (flag2)
			{
				return num4;
			}
			if (!flag)
			{
				return 0;
			}
			return -30000 + arg3;
		}
		Span<ulong> arg6 = stackalloc ulong[256];
		ushort arg7 = 0;
		if (flag4)
		{
			arg7 = field16[num];
		}
		else if (flag3 && arg2 >= 3)
		{
			method1(arg0, arg1, arg2 - 2, arg3, ref arg7, arg5);
		}
		ushort num9 = arg7;
		method0(moveList, arg6, arg3, isWhiteToMove, num9, arg5: false);
		ushort num10 = num9;
		int num11 = -1048576;
		int num12 = 196608;
		ushort arg8 = default;
		for (int i = 0; i < moveList.Length; i++)
		{
			int num13;
			if (num10 != 0)
			{
				num13 = i;
				while (num13 < moveList.Length)
				{
					if (moveList[num13].RawValue != num10)
					{
						num13++;
						continue;
					}
					goto IL_03e2;
				}
				num10 = 0;
			}
			int index = i;
			for (int j = i + 1; j < moveList.Length; j++)
			{
				if (arg6[j] > arg6[index])
				{
					index = j;
				}
			}
			Move move;
			int num14;
			if (arg6[index] == 0)
			{
				move = default;
				num14 = 0;
			}
			else
			{
				move = moveList[index];
				moveList[index] = moveList[i];
				arg6[index] = arg6[i];
				num14 = 1;
			}
			goto IL_04fd;
			IL_0535:
			num10 = 0;
			int num15;
			move = moveList[num15];
			moveList[num15] = moveList[i];
			arg6[num15] = arg6[i];
			int num16 = 1;
			goto IL_0650;
			IL_04fd:
			if (num14 == 0)
			{
				method0(moveList, arg6, arg3, isWhiteToMove, num9, arg5: true);
				if (num10 != 0)
				{
					num15 = i;
					while (num15 < moveList.Length)
					{
						if (moveList[num15].RawValue != num10)
						{
							num15++;
							continue;
						}
						goto IL_0535;
					}
					num10 = 0;
				}
				int index2 = i;
				for (int k = i + 1; k < moveList.Length; k++)
				{
					if (arg6[k] > arg6[index2])
					{
						index2 = k;
					}
				}
				if (arg6[index2] == 0)
				{
					move = default;
					num16 = 0;
				}
				else
				{
					move = moveList[index2];
					moveList[index2] = moveList[i];
					arg6[index2] = arg6[i];
					num16 = 1;
				}
				goto IL_0650;
			}
			goto IL_0655;
			IL_0650:
			if (num16 == 0)
			{
				break;
			}
			goto IL_0655;
			IL_03e2:
			num10 = 0;
			move = moveList[num13];
			moveList[num13] = moveList[i];
			arg6[num13] = arg6[i];
			num14 = 1;
			goto IL_04fd;
			IL_09e1:
			field0.UndoMove(move);
			EvaluationState me2;
			field1 = me2;
			int num17;
			if (num17 > num11)
			{
				num11 = num17;
				arg4 = move.RawValue;
			}
			if (num17 <= arg0)
			{
				continue;
			}
			bool flag7;
			if (num17 >= arg1)
			{
				if (flag7)
				{
					ushort rawValue = move.RawValue;
					for (int l = 1; l < 4; l++)
					{
						ushort num18 = field4[4 * arg3 + l];
						if (num18 == 0 || num18 == rawValue)
						{
							field4[4 * arg3 + l] = field4[4 * arg3];
							break;
						}
					}
					field4[4 * arg3] = rawValue;
					for (int m = 0; m < i; m++)
					{
						Move move2 = moveList[m];
						int num19 = ((!isWhiteToMove) ? 512 : 0) | ((int)move2.MovePieceType << 6) | move2.TargetSquare.Index;
						field8[num19]++;
					}
					uint num20 = (uint)(arg2 * arg2);
					int num21 = ((!isWhiteToMove) ? 512 : 0) | ((int)move.MovePieceType << 6) | move.TargetSquare.Index;
					field5[num21] += num20;
					if (arg3 > 0)
					{
						field6[(field9[arg3 - 1] << 10) | num21] += num20;
					}
					if (arg3 > 1)
					{
						field7[(field9[arg3 - 2] << 10) | num21] += num20;
					}
				}
				num12 = 131072;
				break;
			}
			arg0 = num17;
			num12 = 65536;
			continue;
			IL_0655:
			flag7 = !move.IsCapture && !move.IsPromotion;
			if (flag7 && num5-- == 0)
			{
				break;
			}
			if (((flag6 & flag7) && arg4 != 0) || (flag2 && num4 + field14[(int)move.CapturePieceType] <= arg0) || (flag2 && !move.IsEnPassant && Tables.method0(field0, move, isWhiteToMove) < 0))
			{
				continue;
			}
			field9[arg3] = ((!isWhiteToMove) ? 512 : 0) | ((int)move.MovePieceType << 6) | move.TargetSquare.Index;
			field0.MakeMove(move);
			bool flag8 = field0.IsInCheck();
			me2 = field1;
			ref EvaluationState reference = ref field1;
			int num22 = (int)(move.MovePieceType - 1);
			int num23 = ((!reference.field0) ? 6 : 0);
			reference.field2 -= Tables.field1[(num22 + num23 << 6) | move.StartSquare.Index];
			reference.field1 -= Tables.field0[num22];
			int index3 = move.TargetSquare.Index;
			int num24 = (move.IsPromotion ? ((int)(move.PromotionPieceType - 1)) : num22);
			reference.field2 += Tables.field1[(num24 + num23 << 6) | index3];
			reference.field1 += Tables.field0[num24];
			if (move.IsCapture)
			{
				int num25 = (int)(move.CapturePieceType - 1);
				int num26 = index3;
				if (move.IsEnPassant)
				{
					num26 += (reference.field0 ? (-8) : 8);
				}
				reference.field2 -= Tables.field1[(num25 + (num23 ^ 6) << 6) | num26];
				reference.field1 -= Tables.field0[num25];
			}
			if (move.IsCastles)
			{
				int num27 = index3 & 0x38;
				int num28 = num27;
				if ((index3 & 7) == 2)
				{
					num28 |= 3;
				}
				else
				{
					num27 |= 7;
					num28 |= 5;
				}
				reference.field2 -= Tables.field1[(3 + num23 << 6) | num27];
				reference.field2 += Tables.field1[(3 + num23 << 6) | num28];
			}
			reference.field0 = !reference.field0;
			if (arg4 != 0)
			{
				int num29 = 0;
				if (!flag2)
				{
					int num30 = 0;
					if (flag8)
					{
						num30++;
					}
					num29 = num30;
					if (arg5 + num29 > 6)
					{
						num29 = 6 - arg5;
					}
					if (flag7 && !flag && !flag8 && num29 <= 0 && arg2 >= 3 && i >= 6 && (field12[arg3] == 0 || move.StartSquare.Index != ((field12[arg3] >> 6) & 0x3F) || 1 == 0))
					{
						num29 -= 2;
						num17 = -method1(-arg0 - 1, -arg0, arg2 - 1 + num29, arg3 + 1, ref arg8, arg5);
						if (num17 <= arg0)
						{
							goto IL_09e1;
						}
						num29 = 0;
					}
				}
				num17 = -method1(-arg0 - 1, -arg0, arg2 - 1 + num29, arg3 + 1, ref arg8, arg5 + num29);
				if (num17 <= arg0 || num17 >= arg1)
				{
					goto IL_09e1;
				}
			}
			int num31 = 0;
			if ((!flag2 & flag8) && arg5 < 6)
			{
				num31 = 1;
			}
			num17 = -method1(-arg1, -arg0, arg2 - 1 + num31, arg3 + 1, ref arg8, arg5 + num31);
			goto IL_09e1;
		}
		if (!flag2 || num11 > num4)
		{
			ulong num32 = zobristKey % BoardLens.Mobile.TinyMemory.HashEntries;
			bool flag9 = (field15[num32] & 0xFFFFFFFFFF000000uL) == (zobristKey & 0xFFFFFFFFFF000000uL);
			field15[num32] = (ulong)(ushort)(short)num11 | (ulong)num12 | (ulong)((long)arg2 << 18) | (zobristKey & 0xFFFFFFFFFF000000uL);
			if (!flag9 || num12 != 196608)
			{
				field16[num32] = arg4;
			}
		}
		if (flag2 && num4 > num11)
		{
			return num4;
		}
		return num11;
		IL_0131:
		if (arg3 > 0)
		{
			arg4 = field16[num];
			return (short)num2;
		}
		goto IL_0147;
	}
}
public struct EvaluationState
{
	internal bool field0;

	internal int field1;

	internal ulong field2;

	public int method0()
	{
		int num = field1;
		if (num > 24)
		{
			num = 24;
		}
		short num2 = (short)field2;
		short num3 = (short)(field2 >> 32);
		int num4 = (num2 * num + num3 * (24 - num)) / 24;
		if (!field0)
		{
			return -num4;
		}
		return num4;
	}
}
[StructLayout(LayoutKind.Explicit, Pack = 1, Size = 794)]
internal struct DataBlock
{
}
