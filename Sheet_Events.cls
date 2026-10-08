
Private Sub Worksheet_BeforeDoubleClick(ByVal Target As Range, Cancel As Boolean)
    Dim r As Long
    r = Target.Row
    If r >= 8 And r <= 45 Then
        If Trim(CStr(Me.Cells(r, 2).Value)) <> "" Then
            Cancel = True
            If Trim(CStr(Me.Cells(r, 7).Value)) = "" Then
                Me.Cells(r, 7).Value = "[X] SECILDI"
            Else
                Me.Cells(r, 7).Value = ""
            End If
        End If
    End If
End Sub

Private Sub Worksheet_Change(ByVal Target As Range)
    On Error Resume Next
    If Not Intersect(Target, Me.Range("D3")) Is Nothing Then
        Call SecimleriTemizle
        Exit Sub
    End If
    
    Dim cell As Range, r As Long, c As Long
    If Not Intersect(Target, Me.Range("G8:G45")) Is Nothing Then
        Application.EnableEvents = False
        For Each cell In Intersect(Target, Me.Range("G8:G45"))
            r = cell.Row
            If Trim(CStr(cell.Value)) <> "" Then
                For c = 1 To 7
                    Me.Cells(r, c).Interior.Color = RGB(220, 252, 231)
                Next c
            Else
                For c = 1 To 7
                    If r Mod 2 = 1 Then
                        Me.Cells(r, c).Interior.Color = RGB(248, 250, 252)
                    Else
                        Me.Cells(r, c).Interior.Color = RGB(255, 255, 255)
                    End If
                Next c
            End If
        Next cell
        Application.EnableEvents = True
    End If
End Sub
