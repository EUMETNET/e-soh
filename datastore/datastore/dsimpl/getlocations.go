package dsimpl

import (
	"context"
	"fmt"

	"datastore/common"
	"datastore/datastore"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func (svcInfo *ServiceInfo) GetLocations(
	ctx context.Context, request *datastore.GetLocsRequest) (
	*datastore.GetLocsResponse, error) {

	latest := false // n/a here!
	tspec, err := common.GetTemporalSpec(latest, request.GetTemporalInterval())
	if err != nil {
		return nil, status.Error(
			codes.Internal, fmt.Sprintf("common.GetTemporalSpec() failed: %v", err))
	}

	response, errCode, reason := svcInfo.Sbe.GetLocations(request, tspec)
	if errCode != codes.OK {
		return nil, status.Error(
			errCode, fmt.Sprintf("svcInfo.Sbe.GetLocations() failed: %s", reason))
	}

	return response, nil
}
