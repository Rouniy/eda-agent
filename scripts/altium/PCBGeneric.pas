{ SPDX-License-Identifier: Apache-2.0                                   }
{ Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>                                      }
{..............................................................................}
{ PCBGeneric.pas - PCB object primitives for the Altium integration bridge                  }
{ Parallel to Generic.pas but for PCBServer / IPCB_* objects.               }
{..............................................................................}

{ ObjectTypeFromStringPCB moved to Utils.pas: Library.pas builds BEFORE
  this file and needs it, and a call to a function defined later in the
  concatenation resolves to nothing at runtime. }

{..............................................................................}
{ PCB Property Getter, late-bound, returns '' on unsupported properties     }
{..............................................................................}

Function GetPCBProperty(Obj : IPCB_Primitive; PropName : String) : String;
Var
    Track : IPCB_Track;
    Arc   : IPCB_Arc;
    Pad   : IPCB_Pad;
    Via   : IPCB_Via;
    Fill  : IPCB_Fill;
    Comp  : IPCB_Component;
    Txt   : IPCB_Text;
    Cache : TPadCache;
    Oid   : Integer;
    Rect : TCoordRect;
Begin
    Result := '';
    Try
        Oid := Obj.ObjectId;
        { Base IPCB_Primitive members, valid to read on ANY primitive. }
        If PropName = 'ObjectId'        Then Result := IntToStr(Oid)
        Else If PropName = 'X' Then
        Begin
            If Oid = eViaObject Then Begin Via := Obj; Result := IntToStr(CoordToMils(Via.x)); End
            Else If Oid = ePadObject Then Begin Pad := Obj; Result := IntToStr(CoordToMils(Pad.x)); End
            Else If Oid = eComponentObject Then Begin Comp := Obj; Result := IntToStr(CoordToMils(Comp.x)); End
            Else If Oid = eTextObject Then Begin Txt := Obj; Result := IntToStr(CoordToMils(Txt.XLocation)); End;
        End
        Else If PropName = 'Y' Then
        Begin
            If Oid = eViaObject Then Begin Via := Obj; Result := IntToStr(CoordToMils(Via.y)); End
            Else If Oid = ePadObject Then Begin Pad := Obj; Result := IntToStr(CoordToMils(Pad.y)); End
            Else If Oid = eComponentObject Then Begin Comp := Obj; Result := IntToStr(CoordToMils(Comp.y)); End
            Else If Oid = eTextObject Then Begin Txt := Obj; Result := IntToStr(CoordToMils(Txt.YLocation)); End;
        End
        Else If PropName = 'Address' Then Result := IntToStr(Obj.I_ObjectAddress)
        Else If PropName = 'ComponentDesignator' Then
        Begin
            If Obj.Component <> Nil Then Result := Obj.Component.Name.Text;
        End
        Else If PropName = 'PadName' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Result := Pad.Name; End;
        End
        Else If PropName = 'XCenter_mm' Then
        Begin
            If Oid = eArcObject Then Begin Arc := Obj; Result := FloatToJsonStr(CoordToMM(Arc.XCenter)); End;
        End
        Else If PropName = 'YCenter_mm' Then
        Begin
            If Oid = eArcObject Then Begin Arc := Obj; Result := FloatToJsonStr(CoordToMM(Arc.YCenter)); End;
        End
        Else If PropName = 'Radius_mm' Then
        Begin
            If Oid = eArcObject Then Begin Arc := Obj; Result := FloatToJsonStr(CoordToMM(Arc.Radius)); End;
        End
        Else If PropName = 'BoundsLeft_mm' Then
        Begin
            Rect := Obj.BoundingRectangle; Result := FloatToJsonStr(CoordToMM(Rect.Left));
        End
        Else If PropName = 'BoundsBottom_mm' Then
        Begin
            Rect := Obj.BoundingRectangle; Result := FloatToJsonStr(CoordToMM(Rect.Bottom));
        End
        Else If PropName = 'BoundsRight_mm' Then
        Begin
            Rect := Obj.BoundingRectangle; Result := FloatToJsonStr(CoordToMM(Rect.Right));
        End
        Else If PropName = 'BoundsTop_mm' Then
        Begin
            Rect := Obj.BoundingRectangle; Result := FloatToJsonStr(CoordToMM(Rect.Top));
        End
        Else If PropName = 'IsHidden' Then Result := BoolToJsonStr(Obj.IsHidden)
        Else If PropName = 'X1_mm' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Result := FloatToJsonStr(CoordToMM(Track.X1)); End;
        End
        Else If PropName = 'Y1_mm' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Result := FloatToJsonStr(CoordToMM(Track.Y1)); End;
        End
        Else If PropName = 'X2_mm' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Result := FloatToJsonStr(CoordToMM(Track.X2)); End;
        End
        Else If PropName = 'Y2_mm' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Result := FloatToJsonStr(CoordToMM(Track.Y2)); End;
        End
        Else If PropName = 'Width_mm' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Result := FloatToJsonStr(CoordToMM(Track.Width)); End
            Else If Oid = eArcObject Then Begin Arc := Obj; Result := FloatToJsonStr(CoordToMM(Arc.LineWidth)); End;
        End
        Else If PropName = 'X_mm' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Result := FloatToJsonStr(CoordToMM(Pad.X)); End
            Else If Oid = eTextObject Then Begin Txt := Obj; Result := FloatToJsonStr(CoordToMM(Txt.XLocation)); End;
        End
        Else If PropName = 'Y_mm' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Result := FloatToJsonStr(CoordToMM(Pad.Y)); End
            Else If Oid = eTextObject Then Begin Txt := Obj; Result := FloatToJsonStr(CoordToMM(Txt.YLocation)); End;
        End
        Else If PropName = 'TopXSize_mm' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Result := FloatToJsonStr(CoordToMM(Pad.TopXSize)); End;
        End
        Else If PropName = 'TopYSize_mm' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Result := FloatToJsonStr(CoordToMM(Pad.TopYSize)); End;
        End
        Else If PropName = 'HoleSize_mm' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Result := FloatToJsonStr(CoordToMM(Pad.HoleSize)); End;
        End
        Else If PropName = 'SolderMaskExpansion_mm' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Cache := Pad.GetState_Cache; Result := FloatToJsonStr(CoordToMM(Cache.SolderMaskExpansion)); End;
        End
        Else If PropName = 'SolderMaskBottomExpansion_mm' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Cache := Pad.GetState_Cache; Result := FloatToJsonStr(CoordToMM(Cache.SolderMaskBottomExpansion)); End;
        End
        Else If PropName = 'UseSeparateMaskExpansions' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Cache := Pad.GetState_Cache; Result := BoolToJsonStr(Cache.UseSeparateExpansions); End;
        End
        Else If PropName = 'SolderMaskExpansionMode' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Cache := Pad.GetState_Cache; Result := IntToStr(Cache.SolderMaskExpansionValid); End;
        End
        Else If PropName = 'Layer'      Then Result := GetLayerString(Obj.Layer)
        Else If PropName = 'Descriptor' Then Result := Obj.Descriptor
        Else If PropName = 'Selected'   Then Result := BoolToJsonStr(Obj.Selected)
        { 'Net.Name' is accepted as well as 'Net'. Designator.Text and
          Comment.Text are already accepted alongside their bare forms,
          so a caller who used one of those infers a dotted rule that
          held twice and failed here, silently, returning empty as
          though the copper had no net. Measured: a session concluded
          the bridge could not attribute copper to a net at all and
          stopped, when the property was simply spelled differently. }
        Else If (PropName = 'Net') Or (PropName = 'Net.Name') Then
        Begin
            If Obj.Net <> Nil Then Result := Obj.Net.Name;
        End
        { Subtype members. DelphiScript resolves members against the DECLARED }
        { type, so Obj.X1 on an IPCB_Primitive is "Undeclared identifier".    }
        { Narrow to a typed local via ObjectId (no Forward casts in script).  }
        Else If PropName = 'X1' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Result := IntToStr(CoordToMils(Track.X1)); End
            Else If Oid = eFillObject Then Begin Fill := Obj; Result := IntToStr(CoordToMils(Fill.X1)); End;
        End
        Else If PropName = 'Y1' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Result := IntToStr(CoordToMils(Track.Y1)); End
            Else If Oid = eFillObject Then Begin Fill := Obj; Result := IntToStr(CoordToMils(Fill.Y1)); End;
        End
        Else If PropName = 'X2' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Result := IntToStr(CoordToMils(Track.X2)); End
            Else If Oid = eFillObject Then Begin Fill := Obj; Result := IntToStr(CoordToMils(Fill.X2)); End;
        End
        Else If PropName = 'Y2' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Result := IntToStr(CoordToMils(Track.Y2)); End
            Else If Oid = eFillObject Then Begin Fill := Obj; Result := IntToStr(CoordToMils(Fill.Y2)); End;
        End
        Else If PropName = 'Width' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Result := IntToStr(CoordToMils(Track.Width)); End;
        End
        Else If PropName = 'XCenter' Then
        Begin
            If Oid = eArcObject Then Begin Arc := Obj; Result := IntToStr(CoordToMils(Arc.XCenter)); End;
        End
        Else If PropName = 'YCenter' Then
        Begin
            If Oid = eArcObject Then Begin Arc := Obj; Result := IntToStr(CoordToMils(Arc.YCenter)); End;
        End
        Else If PropName = 'Radius' Then
        Begin
            If Oid = eArcObject Then Begin Arc := Obj; Result := IntToStr(CoordToMils(Arc.Radius)); End;
        End
        Else If PropName = 'StartAngle' Then
        Begin
            If Oid = eArcObject Then Begin Arc := Obj; Result := FloatToStr(Arc.StartAngle); End;
        End
        Else If PropName = 'EndAngle' Then
        Begin
            If Oid = eArcObject Then Begin Arc := Obj; Result := FloatToStr(Arc.EndAngle); End;
        End
        Else If PropName = 'HoleSize' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Result := IntToStr(CoordToMils(Pad.HoleSize)); End
            Else If Oid = eViaObject Then Begin Via := Obj; Result := IntToStr(CoordToMils(Via.HoleSize)); End;
        End
        Else If PropName = 'TopXSize' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Result := IntToStr(CoordToMils(Pad.TopXSize)); End;
        End
        Else If PropName = 'TopYSize' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Result := IntToStr(CoordToMils(Pad.TopYSize)); End;
        End
        Else If PropName = 'TopShape' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Result := IntToStr(Pad.TopShape); End;
        End
        Else If PropName = 'Size' Then
        Begin
            If Oid = eViaObject Then Begin Via := Obj; Result := IntToStr(CoordToMils(Via.Size)); End;
        End
        Else If PropName = 'Rotation' Then
        Begin
            If Oid = eComponentObject Then Begin Comp := Obj; Result := FloatToStr(Comp.Rotation); End
            Else If Oid = ePadObject Then Begin Pad := Obj; Result := FloatToStr(Pad.Rotation); End
            Else If Oid = eTextObject Then Begin Txt := Obj; Result := FloatToStr(Txt.Rotation); End;
        End
        Else If PropName = 'Pattern' Then
        Begin
            If Oid = eComponentObject Then Begin Comp := Obj; Result := Comp.Pattern; End;
        End
        Else If PropName = 'ComponentKind' Then
        Begin
            If Oid = eComponentObject Then Begin Comp := Obj; Result := IntToStr(Comp.ComponentKind); End;
        End
        Else If PropName = 'SourceDesignator' Then
        Begin
            If Oid = eComponentObject Then Begin Comp := Obj; Result := Comp.SourceDesignator; End;
        End
        Else If PropName = 'Name' Then
        Begin
            { Component Name is an IPCB_Text; return its .Text, not the object }
            { (Dispatch->OleStr otherwise crashed EscapeJsonString via modal). }
            If Oid = eComponentObject Then Begin Comp := Obj; Result := Comp.Name.Text; End;
        End
        Else If (PropName = 'Designator') Or (PropName = 'Designator.Text') Then
        Begin
            If Oid = eComponentObject Then Begin Comp := Obj; Result := Comp.Name.Text; End;
        End
        Else If (PropName = 'Comment') Or (PropName = 'Comment.Text') Then
        Begin
            If Oid = eComponentObject Then Begin Comp := Obj; Result := Comp.Comment.Text; End;
        End
        Else If PropName = 'Text' Then
        Begin
            If Oid = eTextObject Then Begin Txt := Obj; Result := Txt.Text; End;
        End;
    Except
        Result := '';
    End;
End;

{..............................................................................}
{ PCB Property Setter                                                        }
{..............................................................................}

Procedure SetPCBProperty(Obj : IPCB_Primitive; PropName : String; Value : String);
Var
    Track : IPCB_Track;
    Arc : IPCB_Arc;
    Pad   : IPCB_Pad;
    Comp  : IPCB_Component;
    Txt   : IPCB_Text;
    Cache : TPadCache;
    NumericValue : Double;
    Oid   : Integer;
Begin
    Try
        Oid := Obj.ObjectId;
        If Pos('_mm', PropName) > 0 Then
        Begin
            NumericValue := StrToFloatDef(Value, -999999);
            If (NumericValue < -10000) Or (NumericValue > 10000) Then Exit;
            If ((PropName = 'Width_mm') Or (PropName = 'Radius_mm')) And (NumericValue <= 0) Then Exit;
        End;
        { Base members, settable on any primitive. }
        If PropName = 'X'             Then Obj.x := MilsToCoord(StrToIntDef(Value, 0))
        Else If PropName = 'Y'        Then Obj.y := MilsToCoord(StrToIntDef(Value, 0))
        Else If PropName = 'XCenter_mm' Then
        Begin
            If Oid = eArcObject Then Begin Arc := Obj; Arc.MoveByXY(MMToCoord(NumericValue) - Arc.XCenter, 0); End;
        End
        Else If PropName = 'Radius_mm' Then
        Begin
            If Oid = eArcObject Then Begin Arc := Obj; Arc.Radius := MMToCoord(NumericValue); End;
        End
        Else If PropName = 'X_mm' Then
        Begin
            If Oid = eTextObject Then Begin Txt := Obj; Txt.MoveByXY(MMToCoord(NumericValue) - Txt.XLocation, 0); End;
        End
        Else If PropName = 'YCenter_mm' Then
        Begin
            If Oid = eArcObject Then Begin Arc := Obj; Arc.MoveByXY(0, MMToCoord(NumericValue) - Arc.YCenter); End;
        End
        Else If PropName = 'Y_mm' Then
        Begin
            If Oid = eTextObject Then Begin Txt := Obj; Txt.MoveByXY(0, MMToCoord(NumericValue) - Txt.YLocation); End;
        End
        Else If PropName = 'X1_mm' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Track.X1 := MMToCoord(NumericValue); End;
        End
        Else If PropName = 'Y1_mm' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Track.Y1 := MMToCoord(NumericValue); End;
        End
        Else If PropName = 'X2_mm' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Track.X2 := MMToCoord(NumericValue); End;
        End
        Else If PropName = 'Y2_mm' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Track.Y2 := MMToCoord(NumericValue); End;
        End
        Else If PropName = 'Width_mm' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Track.Width := MMToCoord(NumericValue); End;
            If Oid = eArcObject Then Begin Arc := Obj; Arc.LineWidth := MMToCoord(NumericValue); End;
        End
        Else If PropName = 'SolderMaskExpansion_mm' Then
        Begin
            If Oid = ePadObject Then
            Begin
                Pad := Obj;
                Cache := Pad.GetState_Cache;
                Cache.SolderMaskExpansionValid := eCacheManual;
                Cache.SolderMaskExpansion := MMToCoord(NumericValue);
                Pad.SetState_Cache := Cache;
            End;
        End
        Else If PropName = 'SolderMaskBottomExpansion_mm' Then
        Begin
            If Oid = ePadObject Then
            Begin
                Pad := Obj;
                Cache := Pad.GetState_Cache;
                Cache.SolderMaskExpansionValid := eCacheManual;
                Cache.UseSeparateExpansions := True;
                Cache.SolderMaskBottomExpansion := MMToCoord(NumericValue);
                Pad.SetState_Cache := Cache;
            End;
        End
        Else If PropName = 'Layer'    Then Obj.Layer := GetLayerFromString(Value)
        Else If PropName = 'Selected' Then Obj.Selected := StrToBool(Value)
        Else If PropName = 'ComponentKind' Then
        Begin
            If Oid = eComponentObject Then Begin Comp := Obj; Comp.ComponentKind := StrToInt(Value); End;
        End
        { Subtype members: narrow to a typed local via ObjectId first. }
        Else If PropName = 'X1' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Track.X1 := MilsToCoord(StrToIntDef(Value, 0)); End;
        End
        Else If PropName = 'Y1' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Track.Y1 := MilsToCoord(StrToIntDef(Value, 0)); End;
        End
        Else If PropName = 'X2' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Track.X2 := MilsToCoord(StrToIntDef(Value, 0)); End;
        End
        Else If PropName = 'Y2' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Track.Y2 := MilsToCoord(StrToIntDef(Value, 0)); End;
        End
        Else If PropName = 'Width' Then
        Begin
            If Oid = eTrackObject Then Begin Track := Obj; Track.Width := MilsToCoord(StrToIntDef(Value, 0)); End;
        End
        Else If PropName = 'Rotation' Then
        Begin
            If Oid = eComponentObject Then Begin Comp := Obj; Comp.Rotation := StrToFloatDef(Value, 0); End
            Else If Oid = ePadObject Then Begin Pad := Obj; Pad.Rotation := StrToFloatDef(Value, 0); End;
        End
        Else If PropName = 'HoleSize' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Pad.HoleSize := MilsToCoord(StrToIntDef(Value, 0)); End;
        End
        Else If PropName = 'TopXSize' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Pad.TopXSize := MilsToCoord(StrToIntDef(Value, 0)); End;
        End
        Else If PropName = 'TopYSize' Then
        Begin
            If Oid = ePadObject Then Begin Pad := Obj; Pad.TopYSize := MilsToCoord(StrToIntDef(Value, 0)); End;
        End
        Else If PropName = 'Text' Then
        Begin
            If Oid = eTextObject Then Begin Txt := Obj; Txt.Text := Value; End;
        End;
    Except
    End;
End;

{..............................................................................}
{ PCB Filter / JSON / Apply, parallel to schematic versions                 }
{..............................................................................}

Function MatchesFilterPCB(Obj : IPCB_Primitive; FilterStr : String) : Boolean;
Var
    Remaining, Condition, PropName, Expected, Actual : String;
    PipePos, EqPos : Integer;
Begin
    Result := True;
    If FilterStr = '' Then Exit;
    Remaining := FilterStr;
    While Remaining <> '' Do
    Begin
        PipePos := Pos('|', Remaining);
        If PipePos > 0 Then
        Begin
            Condition := Copy(Remaining, 1, PipePos - 1);
            Remaining := Copy(Remaining, PipePos + 1, Length(Remaining));
        End
        Else Begin Condition := Remaining; Remaining := ''; End;
        EqPos := Pos('=', Condition);
        If EqPos = 0 Then Continue;
        PropName := Copy(Condition, 1, EqPos - 1);
        Expected := Copy(Condition, EqPos + 1, Length(Condition));
        Actual := GetPCBProperty(Obj, PropName);
        If Actual <> Expected Then Begin Result := False; Exit; End;
    End;
End;

{..............................................................................}
{ IsKnownPCBProperty                                                           }
{                                                                              }
{ Whether GetPCBProperty has a branch for this name. It exists because that    }
{ getter returns '' for anything it does not recognise, which makes a          }
{ MISSPELLED property indistinguishable from one that is genuinely empty. That }
{ ambiguity has now cost three separate investigations, each concluding the    }
{ bridge could not do something it could: the caller sees blanks, believes the }
{ data is not there, and stops.                                                }
{                                                                              }
{ Kept next to the getter deliberately. A list that lives somewhere else       }
{ drifts the first time a branch is added, and a stale allow-list would reject }
{ a property that works, which is worse than the silence it replaces.          }
{..............................................................................}

Function IsKnownPCBProperty(PropName : String) : Boolean;
Begin
    Result :=
        (PropName = 'SolderMaskBottomExpansion_mm') Or (PropName = 'UseSeparateMaskExpansions') Or (PropName = 'Address') Or (PropName = 'ComponentDesignator') Or (PropName = 'PadName') Or (PropName = 'X1_mm') Or (PropName = 'Y1_mm') Or (PropName = 'X2_mm') Or (PropName = 'Y2_mm') Or (PropName = 'Width_mm') Or (PropName = 'X_mm') Or (PropName = 'Y_mm') Or (PropName = 'TopXSize_mm') Or (PropName = 'TopYSize_mm') Or (PropName = 'HoleSize_mm') Or (PropName = 'SolderMaskExpansion_mm') Or (PropName = 'SolderMaskExpansionMode') Or
        (PropName = 'XCenter_mm') Or (PropName = 'YCenter_mm') Or (PropName = 'Radius_mm') Or (PropName = 'BoundsLeft_mm') Or (PropName = 'BoundsBottom_mm') Or (PropName = 'BoundsRight_mm') Or (PropName = 'BoundsTop_mm') Or (PropName = 'IsHidden') Or
        (PropName = 'ObjectId') Or (PropName = 'X') Or (PropName = 'Y') Or
        (PropName = 'Layer') Or (PropName = 'Descriptor') Or
        (PropName = 'Selected') Or (PropName = 'Net') Or
        (PropName = 'Net.Name') Or (PropName = 'X1') Or (PropName = 'Y1') Or
        (PropName = 'X2') Or (PropName = 'Y2') Or (PropName = 'Width') Or
        (PropName = 'Radius') Or (PropName = 'StartAngle') Or
        (PropName = 'EndAngle') Or (PropName = 'XCenter') Or
        (PropName = 'YCenter') Or (PropName = 'HoleSize') Or
        (PropName = 'Size') Or (PropName = 'TopShape') Or
        (PropName = 'TopXSize') Or (PropName = 'TopYSize') Or
        (PropName = 'Rotation') Or (PropName = 'Name') Or
        (PropName = 'Text') Or (PropName = 'Pattern') Or
        (PropName = 'Designator') Or (PropName = 'Designator.Text') Or
        (PropName = 'Comment') Or (PropName = 'Comment.Text') Or
        (PropName = 'SourceDesignator') Or (PropName = 'ComponentKind');
End;

Function UnknownPCBProperties(PropsStr : String) : String;
Var
    Remaining, PropName : String;
    CommaPos : Integer;
Begin
    Result := '';
    Remaining := PropsStr;
    While Remaining <> '' Do
    Begin
        CommaPos := Pos(',', Remaining);
        If CommaPos > 0 Then
        Begin
            PropName := Trim(Copy(Remaining, 1, CommaPos - 1));
            Remaining := Copy(Remaining, CommaPos + 1, Length(Remaining));
        End
        Else Begin PropName := Trim(Remaining); Remaining := ''; End;
        If (PropName <> '') And (Not IsKnownPCBProperty(PropName)) Then
        Begin
            If Result <> '' Then Result := Result + ', ';
            Result := Result + PropName;
        End;
    End;
End;

Function KnownPCBPropertyList : String;
Begin
    Result := 'XCenter_mm, YCenter_mm, Radius_mm, BoundsLeft_mm, BoundsBottom_mm, BoundsRight_mm, BoundsTop_mm, IsHidden, Address, ComponentDesignator, PadName, X1_mm, Y1_mm, X2_mm, Y2_mm, Width_mm, X_mm, Y_mm, TopXSize_mm, TopYSize_mm, HoleSize_mm, SolderMaskExpansion_mm, SolderMaskExpansionMode, ObjectId, X, Y, Layer, Descriptor, Selected, Net, X1, Y1, '
        + 'X2, Y2, Width, Radius, StartAngle, EndAngle, XCenter, YCenter, '
        + 'HoleSize, Size, TopShape, TopXSize, TopYSize, Rotation, Name, '
        + 'Text, Pattern, Designator, Comment, SourceDesignator';
End;

Function BuildObjectJsonPCB(Obj : IPCB_Primitive; PropsStr : String) : String;
Var
    Remaining, PropName, PropValue : String;
    CommaPos : Integer;
    First : Boolean;
Begin
    Result := '{';
    First := True;
    Remaining := PropsStr;
    While Remaining <> '' Do
    Begin
        CommaPos := Pos(',', Remaining);
        If CommaPos > 0 Then
        Begin PropName := Copy(Remaining, 1, CommaPos - 1); Remaining := Copy(Remaining, CommaPos + 1, Length(Remaining)); End
        Else Begin PropName := Remaining; Remaining := ''; End;
        PropValue := GetPCBProperty(Obj, PropName);
        If Not First Then Result := Result + ',';
        First := False;
        Result := Result + '"' + EscapeJsonString(PropName) + '":"' + EscapeJsonString(PropValue) + '"';
    End;
    Result := Result + '}';
End;

Procedure ApplySetPropertiesPCB(Obj : IPCB_Primitive; SetStr : String);
Var
    Remaining, Assignment, PropName, PropValue : String;
    PipePos, EqPos : Integer;
Begin
    Remaining := SetStr;
    While Remaining <> '' Do
    Begin
        PipePos := Pos('|', Remaining);
        If PipePos > 0 Then
        Begin Assignment := Copy(Remaining, 1, PipePos - 1); Remaining := Copy(Remaining, PipePos + 1, Length(Remaining)); End
        Else Begin Assignment := Remaining; Remaining := ''; End;
        EqPos := Pos('=', Assignment);
        If EqPos = 0 Then Continue;
        PropName := Copy(Assignment, 1, EqPos - 1);
        PropValue := Copy(Assignment, EqPos + 1, Length(Assignment));
        SetPCBProperty(Obj, PropName, PropValue);
    End;
End;

{..............................................................................}
{ PCB Board iteration, query/modify/delete on active PCB                    }
{..............................................................................}

Function ProcessPCBBoardObjects(Board : IPCB_Board; ObjTypeInt : Integer;
    FilterStr : String; PropsStr : String; SetStr : String;
    Mode : String; Var TotalMatched : Integer; Limit : Integer) : String;
Var
    Iterator : IPCB_BoardIterator;
    Obj, FoundObj : IPCB_Primitive;
    ObjJson : String;
    First : Boolean;
    MaxIter : Integer;
Begin
    Result := '';
    First := (TotalMatched = 0);

    { EVERY PreProcess BELOW IS IN A Try/Finally, and that is not tidiness.   }
    {                                                                          }
    { An exception anywhere between PreProcess and PostProcess leaves Altium   }
    { believing a command is still running. From then on EVERY save of a PCB   }
    { document is refused with "A command is currently active and save cannot  }
    { be completed at this time", the editor offers to write a copy instead,   }
    { and NOTHING CLEARS IT: not restarting the polling loop, because the      }
    { state lives in the PCB server rather than the script, and not Escape in  }
    { the editor.                                                              }
    {                                                                          }
    { MEASURED on 2026-08-25: a PcbLib and its board went a whole day without  }
    { a successful save while SchLib documents beside them saved normally,     }
    { and the authored footprints existed only in memory.                      }
    {                                                                          }
    { The loop body calls MatchesFilterPCB, BuildObjectJsonPCB and             }
    { ApplySetPropertiesPCB, all of which touch caller-supplied property names }
    { on arbitrary primitives, so raising is an ordinary outcome here rather   }
    { than a remote possibility. AltiumScriptCentral ships a whole recovery    }
    { script for this symptom, which is a fair measure of how often it bites.  }
    If Mode = 'delete' Then
    Begin
        PCBServer.PreProcess;
        Try
            MaxIter := 100000;
            While MaxIter > 0 Do
            Begin
                Iterator := Board.BoardIterator_Create;
                Try
                    Iterator.AddFilter_ObjectSet(MkSet(ObjTypeInt));
                    Iterator.AddFilter_LayerSet(AllLayers);
                    Iterator.AddFilter_Method(eProcessAll);
                    FoundObj := Nil;
                    Obj := Iterator.FirstPCBObject;
                    While Obj <> Nil Do
                    Begin
                        If MatchesFilterPCB(Obj, FilterStr) Then Begin FoundObj := Obj; Break; End;
                        Obj := Iterator.NextPCBObject;
                    End;
                Finally
                    Board.BoardIterator_Destroy(Iterator);
                End;
                If FoundObj = Nil Then Break;
                PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast,
                    PCBM_BoardRegisteration, FoundObj.I_ObjectAddress);
                Board.RemovePCBObject(FoundObj);
                Inc(TotalMatched);
                Dec(MaxIter);
            End;
        Finally
            PCBServer.PostProcess;
        End;
        Exit;
    End;

    If Mode = 'modify' Then PCBServer.PreProcess;
    Try
        Iterator := Board.BoardIterator_Create;
        Try
            Iterator.AddFilter_ObjectSet(MkSet(ObjTypeInt));
            Iterator.AddFilter_LayerSet(AllLayers);
            Iterator.AddFilter_Method(eProcessAll);

            Obj := Iterator.FirstPCBObject;
            While Obj <> Nil Do
            Begin
                If (Limit > 0) And (TotalMatched >= Limit) Then Break;
                If MatchesFilterPCB(Obj, FilterStr) Then
                Begin
                    If Mode = 'query' Then
                    Begin
                        ObjJson := BuildObjectJsonPCB(Obj, PropsStr);
                        If Not First Then Result := Result + ',';
                        First := False;
                        Result := Result + ObjJson;
                    End
                    Else If Mode = 'modify' Then
                        ApplySetPropertiesPCB(Obj, SetStr);
                    Inc(TotalMatched);
                End;
                Obj := Iterator.NextPCBObject;
            End;
        Finally
            Board.BoardIterator_Destroy(Iterator);
        End;
    Finally
        If Mode = 'modify' Then PCBServer.PostProcess;
    End;
End;

Function ProcessActivePCBDoc(ObjTypeInt : Integer;
    FilterStr : String; PropsStr : String; SetStr : String;
    Mode : String; RequestId : String; Limit : Integer) : String;
Var
    Board : IPCB_Board;
    TotalMatched : Integer;
    JsonItems, Why : String;
Begin
    { A READ MAY WANDER; AN EDIT MAY NOT.                                   }
    {                                                                        }
    { GetPCBBoardAnywhere opens the first board it can find when none is     }
    { focused, and hides the focus change afterwards. For a query that is    }
    { the focus-independent access this project advertises. For a delete it  }
    { is a misfire: with a library in front and two boards open, primitives  }
    { would be removed from whichever board the project walk reached first,  }
    { and nothing in the reply would say which.                              }
    {                                                                        }
    { There is no library-scoped primitive delete, so a caller working in a  }
    { PcbLib has no correct tool here and the wrong one used to look like    }
    { it worked.                                                             }
    If (Mode = 'modify') Or (Mode = 'delete') Or (Mode = 'create') Then
    Begin
        Board := GetPCBBoardForMutation(Why);
        If Board = Nil Then
        Begin
            Result := BuildErrorResponse(RequestId, 'AMBIGUOUS_TARGET', Why);
            Exit;
        End;
    End
    Else
        Board := GetPCBBoardAnywhere;

    If Board = Nil Then
    Begin
        Result := BuildErrorResponse(RequestId, 'NO_PCB', 'No PCB document is active');
        Exit;
    End;
    TotalMatched := 0;
    JsonItems := ProcessPCBBoardObjects(Board, ObjTypeInt,
        FilterStr, PropsStr, SetStr, Mode, TotalMatched, Limit);

    If (Mode = 'modify') Or (Mode = 'delete') Or (Mode = 'create') Then
    Begin
        Board.GraphicalView_ZoomRedraw;
        SaveDocByPath(Board.FileName);
    End;

    If Mode = 'query' Then
        Result := BuildSuccessResponse(RequestId,
            '{"objects":[' + JsonItems + '],"count":' + IntToStr(TotalMatched) + '}')
    Else
        Result := BuildSuccessResponse(RequestId,
            '{"matched":' + IntToStr(TotalMatched) + '}');
End;

{..............................................................................}
{ RebuildPCBConnectivity - force Altium to recompute the net topology and the  }
{ ratsnest after primitives were added or removed programmatically.            }
{                                                                              }
{ WHY this is needed at all: adding a track with Board.AddPCBObject makes it   }
{ exist on the board, but the connectivity engine only learns about it from    }
{ the PCBM_BoardRegisteration broadcast, and even then the eConnectionObject   }
{ ratsnest primitives that PCB_GetUnroutedNets counts are only regenerated on  }
{ a connectivity pass. Without one, tracks whose endpoints sit exactly on pad  }
{ centres still read as unrouted -- which is how a fully routed net was        }
{ reported with 2 unrouted connections. A Zoom Redraw (obj_refresh_document)   }
{ repaints, it does not recompute, so it cannot clear this.                    }
{                                                                              }
{ HONESTY NOTE: RunProcess silently ignores process ids it does not know, so   }
{ if 'PCB:UpdateConnectivity' is not a real id on this Altium build this call  }
{ is a no-op and reports nothing. It is used elsewhere in this codebase        }
{ (PCB_TuneLength, where net RoutedLength does change across it), which is the }
{ best evidence available offline. ViewManager_FullUpdate is issued as well    }
{ because it IS a documented IPCB_Board method and is what repaints the newly  }
{ generated ratsnest. Result reports only that the calls were ISSUED without   }
{ raising -- it is not proof the engine actually reran.                        }
{..............................................................................}

Function RebuildPCBConnectivity(Board : IPCB_Board) : Boolean;
Begin
    Result := False;
    If Board = Nil Then Exit;
    Try
        ResetParameters;
        RunProcess('PCB:UpdateConnectivity');
        Result := True;
    Except
    End;
    { Repaint separately: a failed repaint must not mask a successful         }
    { recompute, and vice versa.                                              }
    Try Board.ViewManager_FullUpdate; Except End;
End;
